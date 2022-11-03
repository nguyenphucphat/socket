from http import client
from operator import truediv
import socket
from urllib import response

URL = "http://www-net.cs.umass.edu/wireshark-labs/Wireshark_Intro_v8.1.docx"
SERVER_PORT = 80
FORMAT = "utf8"

def getHostIPAndPath(URL):
    # trường hợp http://
    pos_start = URL.find("//") + 2
    if pos_start == 1:
        pos_start = 0
    pos_end = URL.find("/",pos_start)
    
    if pos_end == -1:
        pos_end = len(URL) - 1
        Host = URL[pos_start:]
    else:
         Host = URL[pos_start:pos_end]
    Path = URL[pos_end+1:]
    return (Host,Path)

def ConnectServerAndRequest(Path, HOSTIP, SERVER_PORT):
    # af_inet cho phải truyền tải dữ liệu ra bên ngoài ipv4
    # sock_stream sử dụng tcp
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect( (socket.gethostbyname(HOSTIP),SERVER_PORT) )
        request_headers = "GET /" + Path + " HTTP/1.1\r\nHost: " + HOSTIP + "\r\nConnection: keep-alive\r\n\r\n"
        
        client.sendall(request_headers.encode())
        return client
    except:
        print("ERROR")
 
def recv_s(client, content_length):
    data = b""
    real_byte = 0
    
    while real_byte != content_length:
        data += client.recv(content_length - real_byte)
        real_byte = len(data)
        
    return data
   
def getHeader(client):
    header = b""
    chunk = b""
    header_delimiter = b"\r\n\r\n"
    
    while header_delimiter not in header:
        chunk = client.recv(1)
        header += chunk
    return header

def getContentLength(header):
    for line in header.split(b'\r\n'):
        if b"Content-Length: " in line:
            pos_start   = line.find(b" ")
            content_length = line[pos_start+1:]   
            return int(content_length)

def getDatabyContentLength(client,content_length):
    data = recv_s(client, content_length)
    return data

def isChunkedEncoding(header):
    signal = b"Transfer-Encoding: chunked"
    
    for line in header.split(b'\r\n'):
        if signal in line: return True
    return False

def getDatabyChunk(client):
    CRLF = b"\r\n"
    data = b""
    size_delimiter = b";"
    while True:
        chunk_size = b""
        while CRLF not in chunk_size:
            chunk_size += client.recv(1)

        if size_delimiter in chunk_size:
            pos = chunk_size.find(size_delimiter)
            size = int(chunk_size[0:pos],16)
        else:  
            size = int(chunk_size[0:len(chunk_size)-2],16)
            
        if size == 0:
            return data
        response = recv_s(client, size + 2)

        data += response[0:len(response)-2]
     
def getFormatName(Path):
    pos = Path.find("/")
    if pos == -1:
        if '.' not in Path:
            return "index.html"
        else: return Path
    
    while True: 
        pos_cur = Path.find("/",pos + 1 ,len(Path))
        if pos_cur == -1:
            return Path[pos + 1:]
        if pos_cur == len(Path) -1:
            return Path[pos +1: len(Path) - 1]
        
        pos = pos_cur

def getFileName(HOST, Path):
    return HOST + '_' + getFormatName(Path)


def dowloadFile(client, header, HOST, Path):
    data = b""
    if isChunkedEncoding(header):
        data = getDatabyChunk(client)
    else:
        content_length = getContentLength(header)
        data = getDatabyContentLength(client,content_length)
    print(len(data))
    
      
    file_name = getFileName(HOST, Path)
    with open(file_name, 'wb') as file:
        file.write(data)
    file.close()

# main function     
(HOST, Path) = getHostIPAndPath(URL)
client = ConnectServerAndRequest(Path,HOST,SERVER_PORT)

header = getHeader(client)
dowloadFile(client,header,HOST,Path)
