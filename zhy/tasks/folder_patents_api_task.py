import argparse
import asyncio
import copy
import json
import math
import os
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests
from loguru import logger


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


DEFAULT_COOKIE_PATH = PROJECT_ROOT / "zhy" / "data" / "other" / "site_init_cookies.json"
DEFAULT_OUTPUT_ROOT_DIR = PROJECT_ROOT / "zhy" / "data" / "output" / "folder_patents_api"
DEFAULT_SPACE_ID = "ccb6031b05034c7ab2c4b120c2dc3155"
DEFAULT_X_CLIENT_ID = "3eea55caeb6247c89952af43ffd8dd03"
DEFAULT_X_DEVICE_ID = "75a24e70-3236-11f1-9806-0519894c2bf7"
DEFAULT_ORIGIN = "https://workspace.zhihuiya.com"
DEFAULT_REFERER = "https://workspace.zhihuiya.com/"
DEFAULT_SITE_LANG = "CN"
DEFAULT_API_VERSION = "2.0"
DEFAULT_PATSNAP_FROM = "w-analytics-workspace"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0"
)
FOLDER_ID_URL_PATH_PATTERN = re.compile(r"/folder/([a-zA-Z0-9]+)/patents")

# 把 mid9 中提取出的 folder_id 粘贴到这里即可直接运行，不传 --folder-id 也能抓取。
DEFAULT_FOLDER_IDS: list[str] = [
  "8614f137547f4e46b8557ae8d3b1e1f5",
  "306f9f76aa5940a0acfc4b8a4dad8a18",
  "7e56feab503f4c0fa5103f7e126a8aa0",
#   "7e80a0c91c024d378441f19a3abc5595",
#   "dc7c0f6fd45e43ca967176d99939f828",
#   "0b77a83bc2554d52b66e6350cb8729f3",
#   "55d9e6fa7c5b4cd6998e2209b386c8c6",
#   "f3abc32038024c398b27fbc853ddb205",
#   "01d62c65b6004f12b53dc784a8c7c3db",
#   "5b8f65fdf98f485b9be7fae53b5f6ed6",
#   "dc7b61795b0e47be8962d13b799a21c7",
#   "f2dc68c92d574b1f848f2266033b014a",
#   "b331ddec5e6c49e59164bfe4fa132427",
#   "1144dcc625ed489ebe790ba2e254f93d",
#   "e63beb68be7f462cac8af8fe51a8df2b",
#   "5d4c2efe21fa4d2aa373c45baa5d61d8",
#   "4b40c13a4e3540f2a728c86d2bfbb2a0",
#   "5ec96a5a1736450b8b0c2342e251e102",
#   "3e2addf18de94f06a56580f3b130fba5",
#   "ee6b594b828140f3a68f2cc0f72d361d",
#   "336870f58f784cf4b4c549ce0f89316a",
#   "009169ef5aee4a43bec38f62cc14f4db",
#   "cb0c191101a2433bb624a75f267d42b6",
#   "65f1ca9627d440d7926106e39bb2c594",
#   "9bb085bc5e80483aa74a27f51c913669",
#   "d187d0a086cd4a92a109f80500226124",
#   "d99392d0fe564269b497d84ed4f31d8e",
#   "45cb70936cd24f05bf3f4fb8c3c72966",
#   "cf26fac1e28245b8a66b81d7e64a47ac",
#   "a249554547b34dc5b4ad82850f544085",
#   "1f9454e94df94dd196df0d0988893f7c",
#   "1962c8210697401ea9cc4213cec0101d",
#   "f34307e6b20c49db8f8927d28485cb67",
#   "f784815ff5634edfb8233f09a265ad7a",
#   "d7abe8b21119497491117e971748af4e",
#   "e5cb6f2045dd4851b748d1e2c4fe7b68",
#   "569b56ad2d7d4189a1a6ee5a124b6b04",
#   "310b60921f0c4400ab3c878ea664397a",
#   "8ae33d07b7d14d0baef1eafe1f0422f6",
#   "1044a5104b36448888c1c05a3cda29a9",
#   "5c36f7e6fa46431d91b1e34c833cc448",
#   "f73f14002fe94bd1a6ab8b0ab427230c",
#   "a86a01c2f58d4daa8a0593ae618cab6d",
#   "7ccce16780624173ae5a3efc2ef9d647",
#   "f5dfc19ec04b47b097ed8beaf6388624",
#   "a962bac504ef477396b881710a7eafad",
#   "edb9160ef53e49e09cfd34ff73a45589",
#   "9cfb7e1877c84906b3379d67b9911065",
#   "5c0aefd4596c472e95dc98790174d8b3",
#   "787a7346edaa4ffc8fc7ae7a603eb6d6",
#   "c45b5a8bd9c9437a8dc6d4c4e9bfa105",
#   "750e84c8956f47548185910ef165b8a5",
#   "c08a3139e0d248918e5a8b592b81f22b",
#   "6d408561684845b8b9fd00b625cf700c",
#   "d6f063dcbf0048e1ae71e526e74b3601",
#   "5fc0db0d625444f5a83f9231ac6bec6a",
#   "2e69f3fc17d7480e8e7134ee7af5467d",
#   "718230c735244402baecad348bb0a4bc",
#   "01b43cd9dac749e4af81ee6b5d212d76",
#   "e95ea4564435411c89ef2d41a52d7ca9",
#   "68044c896d0d4ffaaa3ae20a2a675dc8",
#   "75b63248203d4295ad71a909fa34cea7",
#   "580ad81b850848218970071551fc1a08",
#   "33596c1b7b0e445587353da28ac57498",
#   "2b21dce05f16400ea7593772148ee06a",
#   "4c16bd04d3554bd4ac9d590d885c2237",
#   "6caa6b1093fd4615b2606b1203d3baa3",
#   "793859e128104b6e974870666a735dae",
#   "c2061a741c81430583efefc32e9bfd57",
#   "a3acf4cd05484313a17a039be773527b",
#   "a2bab93e765e4a20853444797910912a",
#   "666aaebea71748509859a860665c38ec",
#   "03fbe996aa134fac835bda7b7766c09c",
#   "950a15fe004c4fa9a965216acde42676",
#   "c88509967b154eaa950b0c96573757e9",
#   "5eba3e34aa9b403bbc825a6a72b17fc2",
#   "c8ceee9e288740eaaf18988364cd3d56",
#   "397bd7fc5aad4e458f6a0452a04bf273",
#   "ad4ea54e4f244eee9ac7c0579b18d176",
#   "a069713d31694a7ea80771429593290f",
#   "30eb6fa113d046c984dfde6c82e905fe",
#   "756fc4f5c3344fb5af553d45ff528220",
#   "7d6a0bc6b8e940198c66df6fef83842d",
#   "57124406db7b4ee3915b1c3113e91dcf",
#   "007c18f329fb40d3897d37fa9a82a150",
#   "2300624a77364e3abbd0279bd5c72320",
#   "71a27f3ef8334824a1ffa55a67e619ab",
#   "eb9746f2b28a4832a7711792648bb63b",
#   "fd057347bfeb4aacafbcbbb4ffec399a",
#   "388b79988a4c4e1b86c48e7fca6a3d49",
#   "77d3ebc45ff641769e0ca6867d1c7c98",
#   "22db9b3fbb384ac4a1f127b3b7e70f4b",
#   "df7bf0881b1544a7a5fb0aa5a92cefee",
#   "83004801a39540b9833d5443efbae40d",
#   "da49b4d09d784eb7a43790c17611b861",
#   "526bb38ad5d34f4b88eb957449c2cc2e",
#   "6088f5943a5441b5b48fa96818efc6fe",
#   "4fb8c7db6a454ed88c6493cdafac1911",
#   "0c30e3cdc9a442368a4fb55a24f2505c",
#   "b0b683c182d14e679773e4d1b8ddef8d",
#   "3d980f6f8f224e72a057292f8735c2ee",
#   "ecf86655edc0489592233f22e986088a",
#   "0d7b8655db3846b1a21a39dae16f4a59",
#   "1486a184ed5f4d3599b251407aaf54a8"
]


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Post to ZHY workspace patents API and save response JSON. "
            "Folders are processed serially, pages are fetched concurrently."
        )
    )
    parser.add_argument("--space-id", default=DEFAULT_SPACE_ID, help="Workspace space id")
    parser.add_argument("--folder-id", action="append", dest="folder_ids", default=[])
    parser.add_argument(
        "--folder-url",
        action="append",
        dest="folder_urls",
        default=[],
        help="Folder URL containing folderId query or /folder/{id}/patents path",
    )
    parser.add_argument(
        "--folder-id-file",
        type=Path,
        help="Text file containing folder ids or folder urls, one item per line",
    )

    parser.add_argument(
        "--token",
        help="Bearer token. If omitted, fallback to env ZHY_BEARER_TOKEN.",
    )
    parser.add_argument("--x-client-id", default=DEFAULT_X_CLIENT_ID)
    parser.add_argument("--x-device-id", default=DEFAULT_X_DEVICE_ID)
    parser.add_argument("--b3", help="Optional b3 tracing header")

    parser.add_argument("--cookie-file", type=Path, default=DEFAULT_COOKIE_PATH)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT_DIR)
    parser.add_argument("--output-file", type=Path)

    parser.add_argument("--origin", default=DEFAULT_ORIGIN)
    parser.add_argument("--referer", default=DEFAULT_REFERER)
    parser.add_argument("--x-site-lang", default=DEFAULT_SITE_LANG)
    parser.add_argument("--x-api-version", default=DEFAULT_API_VERSION)
    parser.add_argument("--x-patsnap-from", default=DEFAULT_PATSNAP_FROM)
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)

    parser.add_argument(
        "--body-file",
        type=Path,
        help="Request body template JSON file. Highest priority.",
    )
    parser.add_argument(
        "--body-json",
        help="Request body template JSON string. Priority lower than --body-file.",
    )
    parser.add_argument("--start-page", type=int, default=1)
    parser.add_argument("--max-pages", type=int)
    parser.add_argument("--page-concurrency", type=int, default=5)
    parser.add_argument("--size", type=int, default=20)

    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--proxy", help="Optional proxy, for example http://127.0.0.1:7890")
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop all folders on first folder failure. Default continues with next folder.",
    )
    return parser


def load_cookie_header(cookie_file: Path) -> str | None:
    if not cookie_file.exists():
        return None

    raw = cookie_file.read_text(encoding="utf-8")
    cookies = json.loads(raw)
    if not isinstance(cookies, list):
        return None

    items: list[str] = []
    for cookie in cookies:
        name = cookie.get("name")
        value = cookie.get("value")
        if not name:
            continue
        if value is None:
            value = ""
        items.append(f"{name}={value}")

    if not items:
        return None
    return "; ".join(items)


def read_json_file_any_utf(path: Path) -> dict:
    text = path.read_text(encoding="utf-8-sig")
    return json.loads(text)


def build_request_body_template(args: argparse.Namespace) -> dict:
    if args.body_file:
        return read_json_file_any_utf(args.body_file)

    if args.body_json:
        return json.loads(args.body_json)

    return {
        "is_init": True,
        "sort": "wtasc",
        "view_type": "tablelist",
        "standard_only": False,
        "page": str(args.start_page),
        "size": args.size,
    }


def extract_folder_id(value: str) -> str | None:
    text = value.strip()
    if not text:
        return None
    if text.startswith("http://") or text.startswith("https://"):
        parsed = urlparse(text)
        query = parse_qs(parsed.query)
        from_query = query.get("folderId")
        if from_query and from_query[0]:
            return from_query[0]
        match = FOLDER_ID_URL_PATH_PATTERN.search(parsed.path)
        if match:
            return match.group(1)
        return None
    return text


def resolve_folder_ids(args: argparse.Namespace) -> list[str]:
    folder_ids: list[str] = []

    for item in args.folder_ids:
        folder_id = extract_folder_id(item)
        if folder_id:
            folder_ids.append(folder_id)

    for item in args.folder_urls:
        folder_id = extract_folder_id(item)
        if folder_id:
            folder_ids.append(folder_id)

    if args.folder_id_file and args.folder_id_file.exists():
        lines = args.folder_id_file.read_text(encoding="utf-8").splitlines()
        for line in lines:
            folder_id = extract_folder_id(line)
            if folder_id:
                folder_ids.append(folder_id)

    if not folder_ids and DEFAULT_FOLDER_IDS:
        folder_ids.extend(DEFAULT_FOLDER_IDS)

    deduped: list[str] = []
    seen: set[str] = set()
    for folder_id in folder_ids:
        if folder_id in seen:
            continue
        seen.add(folder_id)
        deduped.append(folder_id)
    return deduped


def build_headers(args: argparse.Namespace, token: str) -> dict[str, str]:
    headers: dict[str, str] = {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json",
        "origin": args.origin,
        "referer": args.referer,
        "user-agent": args.user_agent,
        "authorization": f"Bearer {token}",
        "x-api-version": args.x_api_version,
        "x-client-id": args.x_client_id,
        "x-device-id": args.x_device_id,
        "x-patsnap-from": args.x_patsnap_from,
        "x-requested-with": "XMLHttpRequest",
        "x-site-lang": args.x_site_lang,
    }

    if args.b3:
        headers["b3"] = args.b3

    cookie_header = load_cookie_header(args.cookie_file)
    if cookie_header:
        headers["cookie"] = cookie_header

    return headers


def build_body_for_page(
    template: dict,
    *,
    space_id: str,
    folder_id: str,
    page: int,
) -> dict:
    body = copy.deepcopy(template)
    body["space_id"] = space_id
    body["folder_id"] = folder_id
    if isinstance(body.get("page"), int):
        body["page"] = page
    else:
        body["page"] = str(page)
    return body


def save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_output_path(args: argparse.Namespace, folder_id: str, page: int, single_folder_mode: bool) -> Path:
    if args.output_file and single_folder_mode and page == args.start_page:
        return args.output_file
    folder_dir = args.output_root / f"{args.space_id}_{folder_id}"
    folder_dir.mkdir(parents=True, exist_ok=True)
    return folder_dir / f"page_{page:04d}.json"


def post_page_sync(
    url: str,
    headers: dict[str, str],
    body: dict,
    timeout_seconds: float,
    proxies: dict[str, str] | None,
) -> dict:
    response = requests.post(
        url,
        headers=headers,
        json=body,
        timeout=timeout_seconds,
        proxies=proxies,
    )
    response.raise_for_status()
    return response.json()


async def post_page_async(
    *,
    page: int,
    url: str,
    headers: dict[str, str],
    body: dict,
    timeout_seconds: float,
    proxies: dict[str, str] | None,
) -> tuple[int, dict]:
    parsed = await asyncio.to_thread(
        post_page_sync,
        url,
        headers,
        body,
        timeout_seconds,
        proxies,
    )
    return page, parsed


async def fetch_folder_patents_async(args: argparse.Namespace) -> Path:
    token = args.token or os.getenv("ZHY_BEARER_TOKEN")
    if not token:
        raise ValueError("missing token: pass --token or set env ZHY_BEARER_TOKEN")

    folder_ids = resolve_folder_ids(args)
    if not folder_ids:
        raise ValueError("no folder ids found: pass --folder-id / --folder-url / --folder-id-file")

    if args.page_concurrency <= 0:
        raise ValueError("page_concurrency must be greater than 0")

    body_template = build_request_body_template(args)
    headers = build_headers(args, token)
    proxies = {"http": args.proxy, "https": args.proxy} if args.proxy else None

    run_summary: dict = {
        "space_id": args.space_id,
        "folders": [],
    }
    last_output_path: Path | None = None
    single_folder_mode = len(folder_ids) == 1

    for folder_id in folder_ids:
        folder_summary = {
            "folder_id": folder_id,
            "status": "ok",
            "reason": "",
            "total": None,
            "limit": None,
            "pages_saved": 0,
            "last_page_requested": None,
            "last_page_patent_count": None,
            "saved_files": [],
            "error": None,
        }
        run_summary["folders"].append(folder_summary)

        url = (
            "https://workspace-service.zhihuiya.com/"
            f"workspace/web/{args.space_id}/folder/{folder_id}/patents"
        )

        try:
            next_page = args.start_page
            while True:
                if args.max_pages is not None:
                    remaining = args.max_pages - folder_summary["pages_saved"]
                    if remaining <= 0:
                        folder_summary["reason"] = "reached_max_pages_limit"
                        break
                    batch_size = min(args.page_concurrency, remaining)
                else:
                    batch_size = args.page_concurrency

                pages = list(range(next_page, next_page + batch_size))
                tasks = []
                for page in pages:
                    body = build_body_for_page(
                        body_template,
                        space_id=args.space_id,
                        folder_id=folder_id,
                        page=page,
                    )
                    tasks.append(
                        asyncio.create_task(
                            post_page_async(
                                page=page,
                                url=url,
                                headers=headers,
                                body=body,
                                timeout_seconds=args.timeout_seconds,
                                proxies=proxies,
                            )
                        )
                    )

                results = await asyncio.gather(*tasks)
                results.sort(key=lambda item: item[0])

                should_stop_folder = False
                for page, parsed in results:
                    output_path = build_output_path(args, folder_id, page, single_folder_mode)
                    save_json(output_path, parsed)
                    last_output_path = output_path

                    folder_summary["saved_files"].append(str(output_path))
                    folder_summary["pages_saved"] += 1
                    folder_summary["last_page_requested"] = page

                    data = parsed.get("data") if isinstance(parsed, dict) else None
                    if not isinstance(data, dict):
                        folder_summary["reason"] = "missing_data_object"
                        should_stop_folder = True
                        break

                    patents_data = data.get("patents_data")
                    patent_count = len(patents_data) if isinstance(patents_data, list) else 0
                    folder_summary["last_page_patent_count"] = patent_count

                    total = data.get("total")
                    limit = data.get("limit")
                    try:
                        total_int = int(total) if total is not None else None
                    except (TypeError, ValueError):
                        total_int = None
                    try:
                        limit_int = int(limit) if limit is not None else None
                    except (TypeError, ValueError):
                        limit_int = None

                    folder_summary["total"] = total_int
                    folder_summary["limit"] = limit_int

                    if patent_count == 0:
                        folder_summary["reason"] = "empty_page_detected"
                        should_stop_folder = True
                        break

                    if total_int is not None and limit_int and limit_int > 0:
                        max_page_by_total = math.ceil(total_int / limit_int)
                        if page >= max_page_by_total:
                            folder_summary["reason"] = "reached_total_page"
                            should_stop_folder = True
                            break

                if should_stop_folder:
                    break

                next_page += batch_size
        except Exception as exc:
            folder_summary["status"] = "error"
            folder_summary["error"] = str(exc)
            if not folder_summary["reason"]:
                folder_summary["reason"] = "request_failed"
            logger.exception(
                "[folder_patents_api_task] folder {} failed: {}",
                folder_id,
                exc,
            )
            if args.fail_fast:
                break

    summary_path = args.output_root / f"{args.space_id}_run_summary.json"
    save_json(summary_path, run_summary)
    logger.info(
        "[folder_patents_api_task] done: folders={} summary={}",
        len(run_summary["folders"]),
        summary_path,
    )

    if last_output_path is not None:
        return last_output_path
    return summary_path


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()
    asyncio.run(fetch_folder_patents_async(args))


if __name__ == "__main__":
    main()
