import math
from multiprocessing import Pool
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import fitz
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def round_up_nearest_10(x):
    return math.ceil(x / 10.0) * 10


class UehDigitallibDownloader:
    BASE_URL = "https://digital.lib.ueh.edu.vn"

    def __init__(
        self,
        cookies_raw: str,
        verify_ssl: bool = False,
        data_path: str | Path = "",
        max_workers: int = 5,
    ) -> None:
        self.cookies = {}
        for cookie in cookies_raw.split(";"):
            key, value = cookie.split("=")
            self.cookies[key] = value
        self.headers = {
            "Accept": "text/javascript, application/javascript, application/ecmascript, application/x-ecmascript, */*; q=0.01",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
        }
        self.verify_ssl = verify_ssl
        if data_path:
            self.data_path = Path(data_path)
        else:
            self.data_path = Path().resolve() / "data"
        self.max_workers = max_workers

    def _check_if_logged_in(self, res_text: str) -> bool:
        login_msg = "Choose Login Method"
        login_status = login_msg not in res_text
        if not login_status:
            raise ValueError("You are not logged in, check your cookies")
        return True

    def parse_doc_url(self, doc_url):
        parsed_url = urlparse(doc_url)
        qs = parse_qs(parsed_url.query)
        subfolder: str = qs["subfolder"][0]
        doc: str = qs["doc"][0]
        bitsid: str = qs["bitsid"][0]
        return {
            "subfolder": subfolder,
            "doc": doc,
            "bitsid": bitsid,
        }

    # def get_num_pages(self, doc_url: str):
    #     res = requests.get(
    #         url=doc_url,
    #         cookies=self.cookies,
    #         headers=self.headers,
    #         verify=False,
    #     )
    #     match = re.search(r"numPages\s+=\s+(\d+);", res.text, re.MULTILINE)
    #     self._check_if_logged_in(res.text)
    #     if match:
    #         return int(match.group(1))
    #     return 0

    def get_page_data(
        self,
        doc_id: str,
        subfolder: str,
        page: int,
        format: str = "json",
    ):
        url = f"{self.BASE_URL}/viewer/services/view.php?doc={doc_id}&format={format}&page={page}&subfolder={subfolder}"
        res = requests.get(
            url=url,
            cookies=self.cookies,
            headers=self.headers,
            verify=False,
        )
        return res

    def get_total_pages(self, doc_url: str):
        doc_url_info = self.parse_doc_url(doc_url)
        doc_id = doc_url_info["doc"]
        subfolder = doc_url_info["subfolder"]
        res = self.get_page_data(
            doc_id=doc_id,
            subfolder=subfolder,
            page=10,
            format="json",
        )
        return res.json()[0]["pages"]

    def get_doc_text(
        self,
        doc_url: str,
        page: int = 10,  # page number must be divisible by 10
    ):
        doc_url_info = self.parse_doc_url(doc_url)
        doc_id = doc_url_info["doc"]
        subfolder = doc_url_info["subfolder"]
        res = self.get_page_data(
            doc_id=doc_id,
            subfolder=subfolder,
            page=round_up_nearest_10(page),
            format="json",
        )
        return res

    def get_doc_image(self, doc_url: str, page: int):
        print(f"Downloading image of page {page}")
        doc_url_info = self.parse_doc_url(doc_url)
        doc_id = doc_url_info["doc"]
        subfolder = doc_url_info["subfolder"]

        file_path = self.data_path / doc_id / f"{page:03d}.jpg"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        if file_path.exists():
            return file_path

        res = self.get_page_data(
            doc_id=doc_id,
            subfolder=subfolder,
            page=page,
            format="jpg",
        )
        if res.status_code == 200:
            with open(file_path, "wb") as f:
                f.write(res.content)
            return file_path
        return None

    def extract_doc_to_jpg(self, doc_url: str):
        print(f"Downloading to jpg document {doc_url}")
        self.data_path.mkdir(parents=True, exist_ok=True)
        total_pages = self.get_total_pages(doc_url)

        arg_list = [(doc_url, page) for page in range(1, total_pages + 1)]
        with Pool(self.max_workers) as pool:
            file_paths = pool.starmap(
                self.get_doc_image,
                arg_list,
            )
        return file_paths

    def extract_doc_to_pdf(self, doc_url: str):
        print(f"Downloading to PDF document {doc_url}")
        img_file_paths = self.extract_doc_to_jpg(doc_url)
        total_pages = len(img_file_paths)
        img_file_paths = [path for path in img_file_paths if path]
        if len(img_file_paths) != total_pages:
            print(f"Warning: {total_pages - len(img_file_paths)} pages are missing")
        img_file_paths = sorted(img_file_paths, key=lambda x: int(x.stem))

        doc_url_info = self.parse_doc_url(doc_url)
        doc_id = doc_url_info["doc"]
        pdf_file_path = self.data_path / f"{doc_id}.pdf"

        doc = fitz.open()
        for ifile in img_file_paths:
            idoc = fitz.open(ifile)
            pdfbytes = idoc.convert_to_pdf()
            doc.insert_pdf(fitz.open("pdf", pdfbytes))

        doc.save(pdf_file_path, garbage=3, deflate=True)

        print(f"PDF saved to {pdf_file_path}")
