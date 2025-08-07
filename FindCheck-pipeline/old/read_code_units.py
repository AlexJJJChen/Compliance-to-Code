import pandas as pd
import os

file_path = os.path.join('old/ComplianceUnitGraph/human_format', '北京证券交易所上市公司持续监管指引第4号——股份回购.xlsx')
df = pd.read_excel(file_path)

# 获取有Code的ComplianceUnit
code_units = df[df['code'].notna()]

print(f"总共有{len(code_units)}个有Code的ComplianceUnit：")
for i, (_, unit) in enumerate(code_units.iterrows(), 1):
    print(f"\n{i}. ComplianceUnit ID: {unit['cu_id']}")
    print(f"   Subject: {unit['subject']}")
    print(f"   Condition: {unit['condition']}")
    print(f"   Constraint: {unit['constraint']}")
    print(f"   Code (部分示例):")
    code_sample = str(unit['code']).strip()
    # 如果代码太长，只显示前15行和最后5行
    lines = code_sample.split('\n')
    if len(lines) > 20:
        print('\n'.join(lines[:15]))
        print("...")
        print('\n'.join(lines[-5:]))
    else:
        print(code_sample)
    print("-" * 80) 