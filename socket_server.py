import os
import socket
from datetime import datetime
from email import policy
from email.parser import BytesParser

class SocketServer:
    def __init__(self):
        self.bufsize = 1024  # 버퍼 크기 설정
        with open('./response.bin', 'rb') as file:
            self.RESPONSE = file.read()  # 응답 파일 읽기
        self.DIR_PATH = './request'
        self.createDir(self.DIR_PATH)

    def createDir(self, path):
        """디렉토리 생성"""
        try:
            if not os.path.exists(path):
                os.makedirs(path)
        except OSError:
            print("Error: Failed to create the directory.")

    def run(self, ip, port):
        """서버 실행"""
        # 소켓 생성
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((ip, port))
        self.sock.listen(10)

        print("Start the socket server...")
        print("\"Ctrl+C\" for stopping the server!\r\n")

        try:
            while True:
                # 클라이언트의 요청 대기
                clnt_sock, req_addr = self.sock.accept()
                clnt_sock.settimeout(5.0)
                print("Request message...\r\n")

                response = b""

                try:
                    # 1. HTTP 헤더 끝까지 받기
                    while b"\r\n\r\n" not in response:
                        chunk = clnt_sock.recv(self.bufsize)
                        if not chunk:
                            raise ValueError("요청 헤더 수신이 중단됐습니다.")
                        response += chunk

                    header, body = response.split(b"\r\n\r\n", 1)

                    # 2. 헤더에서 본문 길이 확인
                    headers = {}
                    for line in header.decode("iso-8859-1").split("\r\n")[1:]:
                        if ":" in line:
                            name, value = line.split(":", 1)
                            headers[name.strip().lower()] = value.strip()

                    content_length = int(headers.get("content-length", "0"))

                    # curl이 전송 허가를 기다리면 먼저 허가 응답
                    if (
                        headers.get("expect", "").lower() == "100-continue"
                        and len(body) < content_length
                    ):
                        clnt_sock.sendall(b"HTTP/1.1 100 Continue\r\n\r\n")

                    # 3. 남은 본문을 끝까지 받기
                    while len(body) < content_length:
                        remaining = content_length - len(body)
                        chunk = clnt_sock.recv(min(self.bufsize, remaining))
                        if not chunk:
                            raise ValueError("요청 본문 수신이 중단됐습니다.")
                        body += chunk
                        response += chunk

                    # 4. 받은 원본을 날짜 이름의 이진 파일로 저장
                    filename = datetime.now().strftime(
                        "%Y-%m-%d-%H-%M-%S.bin"
                    )
                    request_path = os.path.join(self.DIR_PATH, filename)

                    with open(request_path, "wb") as file:
                        file.write(response)

                    print("요청 원본 저장:", request_path)
                    print("저장한 크기:", len(response), "바이트")
                    
                    # 5. HTTP 요청 첫 줄을 제외하고 multipart 해석
                    mime_data = (
                        header.split(b"\r\n", 1)[1]
                        + b"\r\n\r\n"
                        + body
                    )
                    message = BytesParser(
                        policy=policy.default
                    ).parsebytes(mime_data)

                    # 6. image 항목을 찾아 이미지 파일로 저장
                    for part in message.iter_parts():
                        field_name = part.get_param(
                            "name", header="content-disposition"
                        )
                        if field_name != "image":
                            continue

                        image_data = part.get_payload(decode=True)
                        extensions = {
                            "image/png": ".png",
                            "image/jpeg": ".jpg",
                        }
                        extension = extensions.get(
                            part.get_content_type(), ".img"
                        )
                        image_name = (
                            os.path.splitext(filename)[0]
                            + "_image"
                            + extension
                        )
                        image_path = os.path.join(
                            self.DIR_PATH, image_name
                        )

                        with open(image_path, "wb") as file:
                            file.write(image_data)

                        print("이미지 저장:", image_path)
                        break

                except (OSError, ValueError) as error:
                    print("요청 수신 실패:", error)
                    clnt_sock.close()
                    continue

                # 응답 전송
                clnt_sock.sendall(self.RESPONSE)

                # 클라이언트 소켓 닫기
                clnt_sock.close()

        except KeyboardInterrupt:
            print("\r\nStop the server...")

        # 서버 소켓 닫기
        self.sock.close()


if __name__ == "__main__":
    server = SocketServer()
    server.run("127.0.0.1", 8000)