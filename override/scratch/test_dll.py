import ctypes

print("Testing clipboard with restypes...")
try:
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    
    # Set restype/argtypes
    user32.GetClipboardData.restype = ctypes.c_void_p
    user32.GetClipboardData.argtypes = [ctypes.c_uint]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]

    if user32.OpenClipboard(None):
        CF_UNICODETEXT = 13
        if user32.IsClipboardFormatAvailable(CF_UNICODETEXT):
            hData = user32.GetClipboardData(CF_UNICODETEXT)
            print("hData:", hData)
            if hData:
                pData = kernel32.GlobalLock(hData)
                print("pData:", pData)
                if pData:
                    text = ctypes.c_wchar_p(pData).value
                    print("Text:", repr(text))
                    kernel32.GlobalUnlock(hData)
        user32.CloseClipboard()
except Exception as e:
    print("Failed:", e)

print("All tests completed.")
