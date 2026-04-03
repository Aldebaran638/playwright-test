import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tyc.modules.risk_2.risk_daily_converter import convert_risk_results_data, resolve_record_name


def test_convert_risk_results_data_groups_by_company_and_date():
    data = {
        "successful_results": [
            {
                "company_name": "甲公司",
                "success": True,
                "risk_records": [
                    {
                        "title": "标题A",
                        "risk_type": "行政处罚",
                        "fields": {
                            "处罚原因": "产品质量问题",
                            "处罚日期": "2026-04-02",
                        },
                    },
                    {
                        "title": "标题B",
                        "risk_type": "法院公告",
                        "fields": {
                            "公告类型": "起诉状副本及开庭传票",
                            "刊登日期": "2026-04-01",
                        },
                    },
                    {
                        "title": "标题C",
                        "risk_type": "法院公告",
                        "fields": {
                            "案由": "不会被用到",
                            "刊登日期": "2026-04-01",
                        },
                    },
                    {
                        "title": "标题D",
                        "risk_type": "未知类型",
                        "fields": {
                            "发布日期": "2026-04-01",
                        },
                    },
                    {
                        "title": "标题E",
                        "risk_type": "严重违法",
                        "fields": {
                            "违法原因": "虚假宣传",
                        },
                    },
                ],
            },
            {
                "company_name": "乙公司",
                "success": True,
                "risk_records": [
                    {
                        "title": "标题F",
                        "risk_type": "开庭公告",
                        "fields": {
                            "案由": "合同纠纷",
                            "开庭时间": "待定",
                            "发布日期": "2026-04-03",
                        },
                    }
                ],
            },
        ]
    }

    result = convert_risk_results_data(data)

    assert result == [
        {
            "公司名称": "甲公司",
            "时间": "2026-04-01",
            "法律诉讼类型": "法院公告\n法院公告",
            "法律诉讼名称": "起诉状副本及开庭传票\n不会被用到",
            "经营风险类型": "",
            "经营风险名称": "",
        },
        {
            "公司名称": "甲公司",
            "时间": "2026-04-02",
            "法律诉讼类型": "",
            "法律诉讼名称": "",
            "经营风险类型": "行政处罚",
            "经营风险名称": "产品质量问题",
        },
        {
            "公司名称": "乙公司",
            "时间": "2026-04-03",
            "法律诉讼类型": "开庭公告",
            "法律诉讼名称": "合同纠纷",
            "经营风险类型": "",
            "经营风险名称": "",
        },
    ]


def test_resolve_record_name_uses_name_field_array_order_and_title_sentinel():
    fields = {
        "案号": "-",
        "案由": "",
        "备用名称": "有效名称",
        "title": "字段里的假 title",
    }

    assert resolve_record_name("裁判文书", fields, "真正标题") == "真正标题"

    custom_fields = {
        "字段1": "-",
        "字段2": "",
        "字段3": "最终名称",
    }

    assert resolve_record_name_by_fields(["字段1", "字段2", "字段3", "title"], custom_fields, "标题回退") == "最终名称"
    assert resolve_record_name_by_fields(["字段1", "title"], {"字段1": "-"}, "标题回退") == "标题回退"


def resolve_record_name_by_fields(name_fields, fields, title):
    from tyc.modules.risk_2.risk_daily_converter import DEFAULT_NAME_PLACEHOLDER
    from tyc.modules.risk_2.risk_daily_converter import is_valid_name_value, normalize_field_text, normalize_name_fields

    for field_name in normalize_name_fields(name_fields):
        if field_name == "title":
            candidate_value = normalize_field_text(title)
        else:
            candidate_value = normalize_field_text(fields.get(field_name))

        if is_valid_name_value(candidate_value):
            return candidate_value

    return DEFAULT_NAME_PLACEHOLDER