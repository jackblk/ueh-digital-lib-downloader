from multiprocessing import freeze_support

from downloader import UehDigitallibDownloader

DOCUMENT_LINK = "https://digital.lib.ueh.edu.vn/viewer/simple_document.php?subfolder=11/37/11/&doc=113711687779495507995675153871249713696&bitsid=f0396189-d4c0-4cf6-b5e4-2d4157cd1b29&uid=6612a9b5-7ce7-4fbf-b20b-c15a306d546c"

COOKIES_RAW = "!Proxy!viewerPHPSESSID=xxxxxxxxxxxxx; JSESSIONID=xxxxxxxxxxxxxxxxxx"

###################

if __name__ == "__main__":
    freeze_support()
    downloader = UehDigitallibDownloader(
        cookies_raw=COOKIES_RAW,
        max_workers=5,
    )
    downloader.extract_doc_to_pdf(DOCUMENT_LINK)
