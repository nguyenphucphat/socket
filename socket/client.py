import socket
import os
import threading
import sys

SERVER_PORT = 80

# tách host và path khỏi url
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

# kết nối đến server và gửi request
def ConnectServerAndRequest(HOST, Path):
    # af_inet cho phải truyền tải dữ liệu ra bên ngoài ipv4
    # sock_stream sử dụng tcp
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect( (socket.gethostbyname(HOST),SERVER_PORT) )
        request_headers = "GET /" + Path + " HTTP/1.1\r\nHost: " + HOST + "\r\nConnection: keep-alive\r\n\r\n"
        
        client.sendall(request_headers.encode())
        return client
    except:
        print("ERROR")

#  hàm giúp nhận đúng số byte của body
def recv_s(client, content_length):
    data = b""
    real_byte = 0
    
    while real_byte != content_length:
        data += client.recv(content_length - real_byte)
        real_byte = len(data)
        
    return data

# hàm trả về header  
def getHeader(client):
    header = b""
    chunk = b""
    header_delimiter = b"\r\n\r\n"
    # lấy từng byte 1 đến hết body
    while header_delimiter not in header:
        chunk = client.recv(1)
        header += chunk
    return header

# hàm lấy content_length của header
def getContentLength(header):
    for line in header.split(b'\r\n'):
        if b"Content-Length: " in line:
            pos_start   = line.find(b" ")
            content_length = line[pos_start+1:]   
            return int(content_length)

# hàm nhập dữ liệu phần body bằng content_length
def getDatabyContentLength(client,content_length):
    data = recv_s(client, content_length)
    return data

# hàm kiểm tra có truyền dữ liệu kiểu chunk hay không
def isChunkedEncoding(header):
    signal = b"Transfer-Encoding: chunked"
    
    for line in header.split(b'\r\n'):
        if signal in line: return True
    return False

# hàm nhận dữ liệu chia nhỏ thành các chunk
def getDatabyChunk(client):
    CRLF = b"\r\n"
    data = b""
    size_delimiter = b";"
    while True:
        chunk_size = b""
        while CRLF not in chunk_size:
            chunk_size += client.recv(1)
        # lấy chunk size
        if size_delimiter in chunk_size:
            # nếu có phần mở rộng thì bỏ
            pos = chunk_size.find(size_delimiter)
            size = int(chunk_size[0:pos],16)
        else:  
            size = int(chunk_size[0:len(chunk_size)-2],16)
        # nhận luôn 2 byte của CRLF    
        if size == 0:
            return data
        response = recv_s(client, size + 2)

        data += response[0:len(response)-2]

# hàm nhận data phần body
def getDataOfBody(client,header):
    if isChunkedEncoding(header):
        return getDatabyChunk(client)
    else:
        content_length = getContentLength(header)
        return getDatabyContentLength(client,content_length)

# hàm lấy phần format của file       
def getFormatName(Path):
    pos = Path.find("/")
    if pos == -1:
        if '.' not in Path:
            return "index.html"
        else: return Path
    # tìm '/' cuối cùng sau đó là phần format
    while True: 
        pos_cur = Path.find("/",pos + 1 ,len(Path))
        if pos_cur == -1:
            return Path[pos + 1:]
        if pos_cur == len(Path) -1:
            return Path[pos +1: len(Path) - 1]
        
        pos = pos_cur

# hàm trả về tên của fil domain_format
def getFileName(HOST, Path):
    return HOST + '_' + getFormatName(Path)

# kiểm tra có kết nối được đến sever hay không
def isErrorConnection(header):
    if b'HTTP/1.1 200' in header:
        return False
    return True

# hàm download 1 file duy nhất
def downloadOneFile(URL_File, HOST, Path, file_name):
    client = ConnectServerAndRequest(HOST,Path)
    header = getHeader(client)
    if isErrorConnection(header):
        print("Can't connect to server: ",URL_File)
        return False
    data = getDataOfBody(client,header)

    with open(file_name, 'wb') as file:
        file.write(data)
    file.close()
    client.close()
       
# folder
# kiểm trả đường dẫn có dẫn tới folder hay không
def isFolder(Path):
    if Path == "": return False
    # kí tự cuối cùng
    if Path[len(Path)-1] == '/':
        return True
    return False

# tạo 1 luồng request
def handleSever(URL_File, folder_name):
    (HOST_File, Path_File) = getHostIPAndPath(URL_File)
    file_name = folder_name + "\\" + getFormatName(Path_File)
    downloadOneFile(URL_File,HOST_File,Path_File, file_name)
    
# tải toàn bộ file trong folder
def getAllFilesInFolder(URL_Folder,client_folder,folder_name, data_body):
    # tao 1 list để chứa các url
    thread = list()
    # chia nhỏ ra kiểm tra từng đoạn
    for wrap in data_body.split(b'td>'):
        # ví dụ cần tìm:  <td><a href="01-intro.pdf">01-intro.pdf</a></td>
        if b'href=' in wrap:
            pos_start = wrap.find(b'href=') + 6
            pos_end = wrap.find(b'">',pos_start, len(wrap)-1)
            format_name = wrap[pos_start:pos_end]
              
            # không có '.' thì không phải file để tải
            if b'.' not in format_name: continue
            
            # tạo url của file
            URL_File = URL_Folder + format_name.decode()
            thread.append(URL_File)
    # tiến hành tải đa luồng
    for i in range(len(thread)):
        process = threading.Thread(target=handleSever, args=(thread[i],folder_name))
        # process.daemon = True
        process.start()
               

# hàm tải dữ liệu từ 1 đường dẫn bất kì
def downloadFromURL(URL):
    (HOST, Path) = getHostIPAndPath(URL)
   
    file_name = getFileName(HOST,Path)
    # nếu không phải là folder thì tải luôn
    if isFolder(Path) == False:
       downloadOneFile(URL,HOST, Path,file_name)
    else:
        client = ConnectServerAndRequest(HOST, Path)
        header = getHeader(client)
        
        if isErrorConnection(header):
            print("Can't connect to server: ",URL)
            return False
        data_body = getDataOfBody(client,header)
        # tạo 1 folder mới để lưu cái file con
        os.mkdir(file_name)
        # tải xuống tất cả
        getAllFilesInFolder(URL,client, file_name, data_body)
        client.close()

# kết nối đến nhiều sever cùng lúc
def downloadListURLs(list_urls):
    for i in range(len(list_urls)):
        thread = threading.Thread(target=downloadFromURL, args= {list_urls[i]})
        thread.start()

# hàm main       
def main():
    list_urls = list()
    # sử dụng tham số dòng lệnh
    for i  in range(1,len(sys.argv)):
        list_urls.append(str(sys.argv[i]))
   
    downloadListURLs(list_urls)
    
if __name__ == "__main__":
    main()