import logging
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
import grpc
import service_pb2
import service_pb2_grpc

# Конфигурация
app = FastAPI()
GRPC_SERVER_ADDRESS = "grpc_server:50051" 
CHUNK_SIZE = 1024 * 1024 

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.post("/upload/")
async def upload_file(file_name: str, file: UploadFile = File(...)):
    """Маршрут для загрузки файла на сервер через gRPC"""
    async with grpc.aio.insecure_channel(GRPC_SERVER_ADDRESS) as channel:
        stub = service_pb2_grpc.FileServiceStub(channel)

        async def file_chunk_generator():
            """Генератор чанков для отправки файла"""
            while chunk := await file.read(CHUNK_SIZE):
                logger.debug(f"Sending chunk of size {len(chunk)} bytes")
                yield service_pb2.FileUploadRequest(file_name=file_name, chunk_data=chunk)

        try:
            # Отправка файла на gRPC сервер
            response = await stub.UploadFile(file_chunk_generator())
            logger.info(f"File upload completed: {file_name}")
            return {"message": response.message}
        except grpc.RpcError as e:
            logger.error(f"gRPC error during upload: {e}")
            raise HTTPException(status_code=500, detail="Failed to upload file")


@app.get("/download/")
async def download_file(file_name: str):
    """Маршрут для скачивания файла с gRPC сервера"""
    async with grpc.aio.insecure_channel(GRPC_SERVER_ADDRESS) as channel:
        stub = service_pb2_grpc.FileServiceStub(channel)

        async def file_chunk_generator(response, first_chunk=None):
            """Генератор чанков для загрузки файла"""
            if first_chunk:  
                logger.debug(f"Streaming first chunk of size {len(first_chunk.chunk_data)} bytes")
                yield first_chunk.chunk_data
            async for chunk in response:
                logger.debug(f"Streaming chunk of size {len(chunk.chunk_data)} bytes")
                yield chunk.chunk_data

        try:
            logger.info(f"Requesting file: {file_name}")
            response = stub.DownloadFile(service_pb2.FileDownloadRequest(file_name=file_name))

            # Проверка наличия данных (считываем первый чанк)
            async for first_chunk in response:
                if not first_chunk.chunk_data:
                    logger.warning("File not found or empty.")
                    raise HTTPException(status_code=404, detail="File not found or is empty.")

                # Возвращаем поток через StreamingResponse
                return StreamingResponse(
                    file_chunk_generator(response, first_chunk),
                    media_type="application/octet-stream",
                    headers={"Content-Disposition": f"attachment; filename={file_name}"}
                )
        except grpc.RpcError as e:
            logger.error(f"gRPC error during download: {e}")
            raise HTTPException(status_code=500, detail="Failed to download file")


@app.get("/")
async def root():
    """Главная страница для проверки API"""
    return {
        "message": "Welcome to the file storage API. Use /upload/ to upload files and /download/ to retrieve them."
    }
