import pandas as pd
import os

# 获取所有法规文件
regulations_dir = 'old/ComplianceUnitGraph/human_format/'
regulation_files = [f for f in os.listdir(regulations_dir) if f.endswith('.xlsx')]

print("可用的法规文件:")
for file in regulation_files:
    print(f" - {file}")
print()

# 读取股份回购法规文件
file_path = os.path.join(regulations_dir, '北京证券交易所上市公司持续监管指引第4号——股份回购.xlsx')
try:
    print(f"\n读取文件: {os.path.basename(file_path)}")
    df = pd.read_excel(file_path)
    print("列名:")
    print(df.columns.tolist())
    print("\n前5行数据:")
    print(df.head(5))
    
    # 检查relation数据
    print("\nRelation信息统计:")
    relation_counts = df['relation'].value_counts(dropna=True)
    print(relation_counts)
    
    # 检查是否有Code列和数值
    has_code = 'code' in df.columns
    code_count = df['code'].notna().sum() if has_code else 0
    total_count = len(df)
    print(f"\nCode列存在: {has_code}")
    print(f"有Code的行数: {code_count} / {total_count} ({code_count/total_count*100:.2f}%)")
    
except Exception as e:
    print(f"读取文件出错: {e}")

# 检查其他两个法规文件
for other_file in ['北京证券交易所上市公司持续监管指引第8号——股份减持和持股管理.xlsx', 
                  '北京证券交易所上市公司持续监管指引第10号——权益分派.xlsx']:
    try:
        file_path = os.path.join(regulations_dir, other_file)
        print(f"\n\n读取文件: {os.path.basename(file_path)}")
        df = pd.read_excel(file_path)
        print("列名:")
        print(df.columns.tolist())
        print(f"总行数: {len(df)}")
        print("前3行数据:")
        print(df.head(3))
        
        # 检查relation数据
        relation_counts = df['relation'].value_counts(dropna=True) if 'relation' in df.columns else {}
        print("\nRelation信息统计:")
        print(relation_counts)
        
        # 检查是否有Code列和数值
        has_code = 'code' in df.columns
        code_count = df['code'].notna().sum() if has_code else 0
        total_count = len(df)
        print(f"\nCode列存在: {has_code}")
        print(f"有Code的行数: {code_count} / {total_count} ({code_count/total_count*100:.2f}%)")
        
    except Exception as e:
        print(f"读取文件出错: {e}")

# 读取模拟数据样本
print("\n\n模拟数据文件:")
csv_files = [f for f in os.listdir('company_database/') if f.endswith('.csv')]
for csv_file in csv_files:
    print(f" - {csv_file}")

try:
    sample_file = 'company_database/data_simulate_股份回购_04.csv'
    print(f"\n读取模拟数据: {os.path.basename(sample_file)}")
    sample_data = pd.read_csv(sample_file)
    print("模拟数据列名:")
    print(sample_data.columns.tolist())
    print("\n模拟数据前3行:")
    print(sample_data.head(3))
    print(f"\n模拟数据总行数: {len(sample_data)}")
except Exception as e:
    print(f"读取模拟数据出错: {e}") 