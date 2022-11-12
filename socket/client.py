import socket
import os
import threading
import sys

SERVER_PORT = 80

# tách host và path khỏi url
def getHostIPAndPath(URL):
    try:
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
    except:
        return("","")

# kết nối đến server và gửi request
def ConnectServer(HOST, Path):
    # af_inet cho phải truyền tải dữ liệu ra bên ngoài ipv4
    # sock_stream sử dụng tcp
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect( (socket.gethostbyname(HOST),SERVER_PORT) )
    except:
        return client
    return client
        
# gửi request đến sever
def SendRequest(HOST,Path,client):
   try:
        request_headers = "GET /" + Path + " HTTP/1.1\r\nHost: " + HOST + "\r\nConnection: keep-alive\r\n\r\n"
        
        client.sendall(request_headers.encode())
        return client
   except:
       return client

#  hàm giúp nhận đúng số byte của body
def recv_s(client, content_length):
    data = b""
    real_byte = 0
    
    while real_byte != content_length:
        try :
            client.settimeout(10)
            data += client.recv(content_length - real_byte)
        except:
            # nếu khi mất kết nối tới servr hàm recv sẽ treo đến khi time out
            return None
        real_byte = len(data)
        
    return data

# hàm trả về header  
def getHeader(client):
    header = b""
    chunk = b""
    header_delimiter = b"\r\n\r\n"
    # lấy từng byte 1 đến hết body
    while header_delimiter not in header:
        try:
            client.settimeout(10)
            chunk = client.recv(1)
            header += chunk
        except:
            # nếu khi mất kết nối tới servr hàm recv sẽ treo đến khi time out
            return None
            
    return header

# hàm lấy content_length của header
def getContentLength(header):
    try:
        for line in header.split(b'\r\n'):
            if b"Content-Length: " in line:
                pos_start   = line.find(b" ")
                content_length = line[pos_start+1:]   
                return int(content_length)
    except:
        return None
    

# hàm nhập dữ liệu phần body bằng content_length
def getDatabyContentLength(client,header):
    try:
        content_length = getContentLength(header)
        data = recv_s(client, content_length)
        return data
    except:
        return b""

# hàm kiểm tra có truyền dữ liệu kiểu chunk hay không
def isChunkedEncoding(header):
    try:
        signal = b"Transfer-Encoding: chunked"
        
        for line in header.split(b'\r\n'):
            if signal in line: return True
        return False
    except:
        return None

# hàm này giúp vừa nhận dữ liệu bởi các chunk mà không ghi file
def getDatabyChunk(client):
    CRLF = b"\r\n"
    data = b""
    size_delimiter = b";"
    
    while True:
        chunk_size = b""
        while CRLF not in chunk_size:
            try:    
                client.settimeout(10)
                chunk_size += client.recv(1)
            except:
            # nếu khi mất kết nối tới servr hàm recv sẽ treo đến khi time out
                return
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

        if response == None:
            return data
        data += response[0:len(response)-2]
        
# hàm này giúp vừa nhận các chunk vừa ghi file
def Get_SaveDatabyChunk(client,file_name):
    CRLF = b"\r\n"
    data = b""
    size_delimiter = b";"
    
    # mở file
    file = open(file_name,"ab")
    # lấy các chunk
    while True:
        chunk_size = b""
        while CRLF not in chunk_size:
            try:
                client.settimeout(10)
                chunk_size += client.recv(1)
            except:
            # nếu khi mất kết nối tới servr hàm recv sẽ treo đến khi time out
                file.close()
                return  None
        # lấy chunk size
        if size_delimiter in chunk_size:
            # nếu có phần mở rộng thì bỏ
            pos = chunk_size.find(size_delimiter)
            size = int(chunk_size[0:pos],16)
        else:  
            size = int(chunk_size[0:len(chunk_size)-2],16)
        # nhận luôn 2 byte của CRLF    
        if size == 0:
            file.close()
            return data
        response = recv_s(client, size + 2)
        # kiểm tra có mất kết nối trong quá trình nhận file hay không
        if response == None:
            file.close()
        data += response[0:len(data)-2]
        file.write(response[0:len(data)-2])   
    file.close()
        

# hàm lấy phần format của file       
def getFormatName(Path):
    pos = Path.find("/")
    if pos == -1:
        if '.' not in Path:
            return "index.html"
        else: return Path
    # tìm '/' cuối cùng sau đó là phần format
    try:
        while True: 
            pos_cur = Path.find("/",pos + 1 ,len(Path))
            if pos_cur == -1:
                return Path[pos + 1:]
            if pos_cur == len(Path) -1:
                return Path[pos +1: len(Path) - 1]
            
            pos = pos_cur
    except:
        return None

# hàm trả về tên của file domain_format
def getFileName(HOST, Path):
    return HOST + '_' + getFormatName(Path)

# kiểm tra có kết nối được đến sever hay không
def isErrorConnection(header):
    if b'HTTP/1.1 200' in header:
        return False
    return True

# hàm download 1 file duy nhất
def downloadOneFile(URL_File, HOST, Path, file_name,client):
    try:
        client = SendRequest(HOST,Path,client)
        header = getHeader(client)
       
        if isErrorConnection(header):
            return
        
        if isChunkedEncoding(header) == False: 
            data = getDatabyContentLength(client,header)
            with open(file_name, 'wb') as file:
                file.write(data)
            file.close()
        else:
            Get_SaveDatabyChunk(client,file_name)
        
    except:
        return
        
       
# folder
# hàm trả data phần body ( phục vụ cho việc lấy body của folder )
def getDataOfBody(client,header):
    try:
        if isChunkedEncoding(header):
            return getDatabyChunk(client)
        else:
            return getDatabyContentLength(client,header)
    except:
        return
    
# kiểm trả đường dẫn có dẫn tới folder hay không
def isFolder(Path):
    try:
        if Path == "": return False
        # kí tự cuối cùng
        if Path[len(Path)-1] == '/':
            return True
        return False
    except:
        return

# tạo 1 luồng request
def handleSever(URL_File, folder_name, client_folder):
    try:
        (HOST_File, Path_File) = getHostIPAndPath(URL_File)
        file_name = folder_name + "\\" + getFormatName(Path_File)
        client = client_folder
        downloadOneFile(URL_File,HOST_File,Path_File, file_name,client)
    except:
        return

# tải toàn bộ file trong folder
def getAllFilesInFolder(URL_Folder,client_folder,folder_name, data_body):
    try:
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
        # gửi nhiều request trong 1 connection
        for i in range(len(thread)):
            handleSever(thread[i],folder_name,client_folder)    
    except:
        return

# hàm xử lý khi tên folder trùng
def mkdir_s(file_name):
    first_name = file_name
    i = 0
    while True:
        try:
             os.mkdir(file_name)
             return file_name
        except:
            i+=1
            file_name = first_name +"("+str(i)+")"
            
                          
# hàm tải dữ liệu từ 1 đường dẫn bất kì
def downloadFromURL(URL):
    try:
        (HOST, Path) = getHostIPAndPath(URL)
    
        file_name = getFileName(HOST,Path)
        client = ConnectServer(HOST, Path)
        
        # nếu không phải là folder thì tải luôn
        if isFolder(Path) == False:
            downloadOneFile(URL,HOST, Path,file_name,client)
        else:
            client = SendRequest(HOST,Path,client)
            header = getHeader(client)
        
            if isErrorConnection(header):
                return
            data_body = getDataOfBody(client,header)
            # tạo 1 folder mới để lưu cái file con
            file_name = mkdir_s(file_name)
            # tải xuống tất cả
            getAllFilesInFolder(URL,client, file_name, data_body)
            client.close()
    except:
        return

# kết nối đến nhiều sever cùng lúcs
def downloadListURLs(list_urls):
    for i in range(len(list_urls)):
        thread = threading.Thread(target=downloadFromURL, args= {list_urls[i]})
        thread.start()

# hàm main       
def main():
    try:
        list_urls = list()
        # sử dụng tham số dòng lệnh
        for i  in range(1,len(sys.argv)):
            list_urls.append(str(sys.argv[i]))
        downloadListURLs(list_urls)
    except:
        return
    
# chỉ hàm main trong file này mới được chạy
if __name__ == "__main__":
    main()