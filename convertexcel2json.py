import json
from pathlib import Path
from typing import Iterable

import pandas as pd


def _get_value(row: pd.Series, candidates: Iterable[str]) -> object:
	for name in candidates:
		if name in row.index:
			value = row.get(name)
			return None if pd.isna(value) else value
	return None


def excel_to_json(excel_path: Path, sheet_name: str, output_path: Path) -> None:
	df = pd.read_excel(excel_path, sheet_name=sheet_name)
	rows = df.where(pd.notnull(df), None).to_dict(orient="records")

	records = []
	for row_dict in rows:
		row = pd.Series(row_dict)
		record = {
			"age": _get_value(row, ["年龄", "age", "Age"]),
			"I": {
				"a": {
					"疾病名称": _get_value(
						row,
						[
							"a:直接导致死亡的疾病",
							"a直接导致死亡的疾病",
							"I-a疾病",
						],
					),
					"ICD10编码": _get_value(
						row,
						[
							"a:直接导致死亡的疾病ICD10编码",
							"a直接导致死亡的疾病ICD10编码",
							"I-a疾病ICD10编码",
						],
					),
					"发病到死亡的时间间隔": _get_value(
						row,
						[
							"a:发病到死亡的时间间隔",
							"a发病到死亡的时间间隔",
							"I-a发病到死亡的时间间隔",
						],
					),
					"发病到死亡的时间间隔单位": _get_value(
						row,
						[
							"a:发病到死亡的时间间隔单位",
							"a发病到死亡的时间间隔单位",
							"I-a发病到死亡的时间间隔单位",
						],
					),
				},
				"b": {
					"疾病名称": _get_value(
						row,
						[
							"b:直接导致死亡的疾病",
							"b直接导致死亡的疾病",
							"I-b疾病",
						],
					),
					"ICD10编码": _get_value(
						row,
						[
							"b:直接导致死亡的疾病ICD10编码",
							"b直接导致死亡的疾病ICD10编码",
							"I-b疾病ICD10编码",
						],
					),
					"发病到死亡的时间间隔": _get_value(
						row,
						[
							"b:发病到死亡的时间间隔",
							"b发病到死亡的时间间隔",
							"I-b发病到死亡的时间间隔",
						],
					),
					"发病到死亡的时间间隔单位": _get_value(
						row,
						[
							"b:发病到死亡的时间间隔单位",
							"b发病到死亡的时间间隔单位",
							"I-b发病到死亡的时间间隔单位",
						],
					),
				},
				"c": {
					"疾病名称": _get_value(
						row,
						[
							"c:直接导致死亡的疾病",
							"c直接导致死亡的疾病",
							"I-c疾病",
						],
					),
					"ICD10编码": _get_value(
						row,
						[
							"c:直接导致死亡的疾病ICD10编码",
							"c直接导致死亡的疾病ICD10编码",
							"I-c疾病ICD10编码",
						],
					),
					"发病到死亡的时间间隔": _get_value(
						row,
						[
							"c:发病到死亡的时间间隔",
							"c发病到死亡的时间间隔",
							"I-c发病到死亡的时间间隔",
						],
					),
					"发病到死亡的时间间隔单位": _get_value(
						row,
						[
							"c:发病到死亡的时间间隔单位",
							"c发病到死亡的时间间隔单位",
							"I-c发病到死亡的时间间隔单位",
						],
					),
				},
				"d": {
					"疾病名称": _get_value(
						row,
						[
							"d:直接导致死亡的疾病",
							"d直接导致死亡的疾病",
							"I-d疾病",
						],
					),
					"ICD10编码": _get_value(
						row,
						[
							"d:直接导致死亡的疾病ICD10编码",
							"d直接导致死亡的疾病ICD10编码",
							"I-d疾病ICD10编码",
						],
					),
					"发病到死亡的时间间隔": _get_value(
						row,
						[
							"d:发病到死亡的时间间隔",
							"d发病到死亡的时间间隔",
							"I-d发病到死亡的时间间隔",
						],
					),
					"发病到死亡的时间间隔单位": _get_value(
						row,
						[
							"d:发病到死亡的时间间隔单位",
							"d发病到死亡的时间间隔单位",
							"I-d发病到死亡的时间间隔单位",
						],
					),
				},
			},
			"II": {
				"其它疾病诊断": _get_value(
					row,
					["其它疾病诊断", "其他疾病诊断", "II其它疾病诊断"],
				),
				"其它疾病诊断ICD10编码": _get_value(
					row,
					[
						"其它疾病诊断ICD10编码",
						"其他疾病诊断ICD10编码",
						"II其它疾病诊断ICD10编码",
					],
				),
			},
			"root_cause": {
				"根本死亡原因": _get_value(
					row,
					["根本死亡原因", "根本死因"],
				),
				"根本死亡原因编码": _get_value(
					row,
					["根本死亡原因编码", "根本死因编码"],
				),
			},
		}
		records.append(record)

	with output_path.open("w", encoding="utf-8") as handle:
		json.dump(records, handle, ensure_ascii=False, indent=2)


def main() -> None:
	base_dir = Path(__file__).resolve().parent
	excel_path = base_dir / "data.xlsx"
	output_path = base_dir / "data.json"

	excel_to_json(excel_path, sheet_name="卡片", output_path=output_path)


if __name__ == "__main__":
	main()



