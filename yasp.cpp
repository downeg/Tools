include <Windows.h>
#include <iostream>
#include <string>
#include <vector>
#include <cctype>

/*
    yasp.exe
    Yet Another String Parser.
    @author: downeg.ie
*/

int main(int argc, char* argv[]) {

    if (argc < 2) {
        std::cerr << "Usage: " << argv[0] << " <filename> [string min length]\n";
        return 1;
    }

    int minLength = (argc >= 3) ? std::stoi(argv[2]) : 4;

    HANDLE hFile = CreateFileA(
        argv[1],
        GENERIC_READ,
        0,
        NULL,
        OPEN_EXISTING,
        NULL,
        NULL
    );

    if (hFile != INVALID_HANDLE_VALUE) {

        char byte;
        DWORD bytesRead;
        std::vector<char> buffer;

        while (ReadFile(hFile, &byte, 1, &bytesRead, NULL) && bytesRead == 1) {
            if (isprint(byte)) {   
//std::isprint Defined in header <cctype>: Checks if ch is a printable character as classified by the currently installed C locale.
                buffer.push_back(byte);
            }
            else {
                if (buffer.size() >= minLength) {
                    std::cout.write(buffer.data(), buffer.size());
                    std::cout << "\n";
                }
                buffer.clear();
            }
        }

        CloseHandle(hFile);
    }
    else {

        std::cerr << "[-] Error: Could not open file: " << GetLastError() << std::endl;
        return 1;
    }

	return 0;
}
