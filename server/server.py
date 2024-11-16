import grpc
import os
import asyncio
import logging
import service_pb2
import service_pb2_grpc

# Константы
FILE_STORAGE_DIRECTORY = "./storage"
CHUNK_SIZE = 1024 * 1024 

# Создание каталога для хранения файлов
os.makedirs(FILE_STORAGE_DIRECTORY, exist_ok=True)

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class FileService(service_pb2_grpc.FileServiceServicer):
    async def UploadFile(self, request_iterator, context):
        """Метод для загрузки файла на сервер по частям."""
        logger.debug("UploadFile method called")

        try:
            # Получение первого чанка для извлечения имени файла
            first_request = await request_iterator.__anext__()
            
            file_name = first_request.file_name
            file_path = os.path.join(FILE_STORAGE_DIRECTORY, file_name)

            logger.debug(f"Начало загрузки файла: {file_name} в {file_path}")

            # Сохранение файла по частям
            with open(file_path, "wb") as f:
                f.write(first_request.chunk_data)
                async for request in request_iterator:
                    f.write(request.chunk_data)

            logger.info(f"Файл {file_name} успешно загружен.")
            return service_pb2.FileUploadResponse(message="File uploaded successfully.")

        except StopAsyncIteration:
            logger.error("Не был передан файл или данные.")
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("No file data provided")
            return service_pb2.FileUploadResponse(message="No file data provided.")

        except Exception as e:
            logger.error(f"Ошибка во время загрузки файла: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Error during file upload")
            return service_pb2.FileUploadResponse(message="Error during file upload.")

    async def DownloadFile(self, request, context):
        """Метод для скачивания файла с сервера по частям."""
        logger.debug("DownloadFile method called")
        file_path = os.path.join(FILE_STORAGE_DIRECTORY, request.file_name)

        logger.debug(f"Проверка наличия файла по пути: {file_path}")

        # Проверка наличия файла
        if not os.path.exists(file_path):
            logger.warning(f"Файл не найден: {file_path}")
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("File not found")
            return

        # Проверка, что файл не пустой
        if os.path.getsize(file_path) == 0:
            logger.warning(f"Файл пустой: {file_path}")
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("File is empty")
            return

        try:
            # Чтение файла и отправка чанков клиенту
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    yield service_pb2.FileDownloadResponse(chunk_data=chunk)

            logger.info(f"Файл {request.file_name} успешно отправлен клиенту.")
        except Exception as e:
            logger.error(f"Ошибка во время скачивания файла: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Error during file download")


async def serve():
    """Функция запуска gRPC-сервера."""
    server = grpc.aio.server()
    service_pb2_grpc.add_FileServiceServicer_to_server(FileService(), server)
    server.add_insecure_port("[::]:50051")
    logger.info("gRPC сервер запускается на порту 50051")
    await server.start()
    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(serve())
