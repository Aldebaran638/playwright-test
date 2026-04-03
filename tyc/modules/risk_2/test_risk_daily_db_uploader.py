import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tyc.modules.risk_2.risk_daily_db_uploader import extract_summary_records_from_data


def test_extract_summary_records_from_data_skips_invalid_rows():
    data = [
        {
            "公司名称": "甲公司",
            "时间": "2026-04-01",
            "法律诉讼类型": "法院公告",
            "法律诉讼名称": "起诉状副本及开庭传票",
            "经营风险类型": "",
            "经营风险名称": "",
        },
        {
            "公司名称": "",
            "时间": "2026-04-02",
            "法律诉讼类型": "",
            "法律诉讼名称": "",
            "经营风险类型": "行政处罚",
            "经营风险名称": "产品质量问题",
        },
        {
            "公司名称": "乙公司",
            "时间": "20260403",
            "法律诉讼类型": "开庭公告",
            "法律诉讼名称": "合同纠纷",
            "经营风险类型": "",
            "经营风险名称": "",
        },
    ]

    result = extract_summary_records_from_data(data)

    assert result == [
        {
            "company_name": "甲公司",
            "risk_date": "2026-04-01",
            "legal_litigation_types": "法院公告",
            "legal_litigation_names": "起诉状副本及开庭传票",
            "business_risk_types": "",
            "business_risk_names": "",
        }
    ]