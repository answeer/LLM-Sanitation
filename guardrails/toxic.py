import json
import re
import os
import glob
from collections import defaultdict
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_similarity
import openai
from typing import List, Dict, Any, Tuple
import time

class KeyStandardizer:
    def __init__(self, openai_api_key: str = None):
        """
        初始化Key标准化器
        
        Args:
            openai_api_key: OpenAI API密钥
        """
        if openai_api_key:
            openai.api_key = openai_api_key
        else:
            openai.api_key = os.getenv('OPENAI_API_KEY')
        
    def load_json_from_folder(self, folder_path: str, pattern: str = "*.json") -> List[Dict]:
        """
        从文件夹加载所有JSON文件
        
        Args:
            folder_path: 文件夹路径
            pattern: 文件匹配模式
            
        Returns:
            JSON数据列表
        """
        all_data = []
        json_files = glob.glob(os.path.join(folder_path, pattern))
        
        if not json_files:
            print(f"在文件夹 {folder_path} 中没有找到 {pattern} 文件")
            return all_data
        
        print(f"找到 {len(json_files)} 个JSON文件")
        
        for file_path in json_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    all_data.append({
                        'file_path': file_path,
                        'data': data
                    })
                print(f"成功加载: {os.path.basename(file_path)}")
            except Exception as e:
                print(f"加载文件 {file_path} 时出错: {e}")
        
        return all_data
    
    def extract_all_keys(self, json_data_list: List[Dict]) -> List[str]:
        """
        从所有JSON数据中提取所有唯一的key
        
        Args:
            json_data_list: JSON数据列表（包含文件路径和数据的字典）
            
        Returns:
            所有唯一的key列表
        """
        all_keys = set()
        
        for item in json_data_list:
            data = item['data']
            
            # 提取key_values中的key
            if 'key_values' in data:
                for kv in data['key_values']:
                    if 'key' in kv:
                        all_keys.add(kv['key'])
            
            # 提取其他可能包含key的字段
            self._extract_keys_from_dict(data, all_keys)
        
        return list(all_keys)
    
    def _extract_keys_from_dict(self, data: Dict, keys_set: set, prefix: str = ""):
        """
        递归从字典中提取所有key
        
        Args:
            data: 字典数据
            keys_set: 存储key的集合
            prefix: 键前缀
        """
        if not isinstance(data, dict):
            return
            
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            keys_set.add(full_key)
            
            if isinstance(value, dict):
                self._extract_keys_from_dict(value, keys_set, full_key)
            elif isinstance(value, list) and value:
                for item in value:
                    if isinstance(item, dict):
                        self._extract_keys_from_dict(item, keys_set, full_key)
    
    def preprocess_keys(self, keys: List[str]) -> List[str]:
        """
        预处理key文本
        
        Args:
            keys: 原始key列表
            
        Returns:
            预处理后的key列表
        """
        processed_keys = []
        for key in keys:
            # 移除特殊字符和数字，保留字母、空格和下划线
            cleaned = re.sub(r'[^a-zA-Z\s_]', ' ', key)
            # 将驼峰命名转换为空格分隔
            cleaned = re.sub(r'([a-z])([A-Z])', r'\1 \2', cleaned)
            # 将下划线转换为空格
            cleaned = cleaned.replace('_', ' ')
            # 移除多余空格并转为小写
            cleaned = ' '.join(cleaned.lower().split())
            processed_keys.append(cleaned)
        return processed_keys
    
    def cluster_keys(self, keys: List[str], processed_keys: List[str]) -> Dict[int, List[str]]:
        """
        使用TF-IDF和DBSCAN对key进行聚类
        
        Args:
            keys: 原始key列表
            processed_keys: 预处理后的key列表
            
        Returns:
            聚类结果字典 {cluster_id: [keys]}
        """
        if len(keys) <= 1:
            return {0: keys} if keys else {}
        
        # 创建TF-IDF向量化器
        vectorizer = TfidfVectorizer(
            min_df=1,
            max_df=0.8,
            stop_words='english',
            ngram_range=(1, 2)
        )
        
        try:
            # 生成TF-IDF矩阵
            tfidf_matrix = vectorizer.fit_transform(processed_keys)
            
            # 使用DBSCAN进行聚类
            dbscan = DBSCAN(
                eps=0.3,  # 聚类半径
                min_samples=2,  # 最小样本数
                metric='cosine'
            )
            
            clusters = dbscan.fit_predict(tfidf_matrix)
            
            # 组织聚类结果
            cluster_results = defaultdict(list)
            for key, cluster_id in zip(keys, clusters):
                cluster_results[cluster_id].append(key)
            
            return dict(cluster_results)
            
        except Exception as e:
            print(f"聚类过程中出错: {e}")
            # 如果聚类失败，将每个key作为单独的簇
            return {i: [key] for i, key in enumerate(keys)}
    
    def call_llm_for_standardization(self, key_group: List[str], retries: int = 3) -> str:
        """
        调用LLM为key组生成标准化名称
        
        Args:
            key_group: 同一聚类中的key列表
            retries: 重试次数
            
        Returns:
            标准化的key名称
        """
        for attempt in range(retries):
            try:
                prompt = self._create_standardization_prompt(key_group)
                
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that standardizes key names for document processing. Provide concise, clear, and consistent key names."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    max_tokens=50
                )
                
                standardized_key = response.choices[0].message.content.strip()
                return standardized_key
                
            except Exception as e:
                print(f"LLM调用失败 (尝试 {attempt + 1}/{retries}): {e}")
                if attempt < retries - 1:
                    time.sleep(2)  # 等待后重试
        
        # 如果所有重试都失败，使用启发式方法
        print(f"所有LLM重试失败，使用启发式方法处理: {key_group}")
        return self._heuristic_standardization(key_group)
    
    def _create_standardization_prompt(self, key_group: List[str]) -> str:
        """
        创建标准化提示
        
        Args:
            key_group: key列表
            
        Returns:
            LLM提示文本
        """
        keys_str = "\n".join([f"- {key}" for key in key_group])
        
        return f"""
        I have a group of similar keys from document processing that need to be standardized into a single, consistent key name.
        
        Key group:
        {keys_str}
        
        Please analyze these keys and provide ONE standardized key name that best represents the common meaning of all keys in this group.
        
        Requirements:
        1. Be concise and descriptive
        2. Use snake_case format (words separated by underscores)
        3. Make it clear what data the key represents
        4. Avoid unnecessary words
        5. Keep it under 5 words if possible
        
        Provide only the standardized key name, no explanations.
        Standardized key:"""
    
    def _heuristic_standardization(self, key_group: List[str]) -> str:
        """
        启发式标准化方法（当LLM不可用时使用）
        
        Args:
            key_group: key列表
            
        Returns:
            启发式生成的标准化key
        """
        if not key_group:
            return ""
        
        # 选择最长的key作为基础（通常包含最多信息）
        base_key = max(key_group, key=len)
        
        # 清理key
        cleaned = re.sub(r'[^a-zA-Z\s]', ' ', base_key)
        cleaned = re.sub(r'([a-z])([A-Z])', r'\1 \2', cleaned)
        words = cleaned.lower().split()
        
        # 移除常见停用词
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        meaningful_words = [word for word in words if word not in stop_words and len(word) > 2]
        
        if not meaningful_words:
            meaningful_words = words[:3]  # 如果没有有意义的词，取前三个
        
        # 转换为snake_case
        standardized = '_'.join(meaningful_words[:4])  # 最多4个词
        
        return standardized
    
    def standardize_keys_from_folder(self, folder_path: str, pattern: str = "*.json") -> Dict[str, Any]:
        """
        主函数：标准化文件夹中所有JSON文件中的key
        
        Args:
            folder_path: 包含JSON文件的文件夹路径
            pattern: 文件匹配模式
            
        Returns:
            标准化结果字典
        """
        print(f"开始处理文件夹: {folder_path}")
        
        # 加载数据
        json_data = self.load_json_from_folder(folder_path, pattern)
        if not json_data:
            return {"error": "没有找到可用的JSON数据"}
        
        # 提取keys
        print("提取keys...")
        all_keys = self.extract_all_keys(json_data)
        print(f"找到 {len(all_keys)} 个唯一的key")
        
        if not all_keys:
            return {"error": "没有找到任何key"}
        
        # 预处理
        print("预处理keys...")
        processed_keys = self.preprocess_keys(all_keys)
        
        # 聚类
        print("对keys进行聚类...")
        clusters = self.cluster_keys(all_keys, processed_keys)
        
        # 标准化
        print("为每个聚类生成标准化名称...")
        standardization_map = {}
        cluster_standard_names = {}
        
        total_clusters = len(clusters)
        for i, (cluster_id, key_group) in enumerate(clusters.items()):
            print(f"处理聚类 {i+1}/{total_clusters} (包含 {len(key_group)} 个keys)")
            
            if cluster_id == -1:  # 噪声点，每个key单独处理
                for key in key_group:
                    standardized = self.call_llm_for_standardization([key])
                    standardization_map[key] = standardized
                    cluster_standard_names[key] = standardized
            else:
                standardized = self.call_llm_for_standardization(key_group)
                cluster_standard_names[f"cluster_{cluster_id}"] = standardized
                for key in key_group:
                    standardization_map[key] = standardized
            
            # 添加小延迟避免API限制
            time.sleep(1)
        
        # 生成最终报告
        result = {
            'folder_processed': folder_path,
            'total_files': len(json_data),
            'total_keys': len(all_keys),
            'total_clusters': len([cid for cid in clusters.keys() if cid != -1]),
            'noise_keys': len(clusters.get(-1, [])),
            'standardization_mapping': standardization_map,
            'cluster_standard_names': cluster_standard_names,
            'clusters_detail': clusters,
            'all_keys_found': all_keys
        }
        
        return result
    
    def save_results(self, results: Dict, output_file: str):
        """
        保存标准化结果
        
        Args:
            results: 标准化结果
            output_file: 输出文件路径
        """
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else '.', exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"结果已保存到: {output_file}")
    
    def generate_mapping_file(self, results: Dict, mapping_file: str):
        """
        生成易于使用的映射文件
        
        Args:
            results: 标准化结果
            mapping_file: 映射文件路径
        """
        if 'standardization_mapping' not in results:
            print("没有找到标准化映射数据")
            return
        
        mapping = results['standardization_mapping']
        
        # 按标准化名称分组
        grouped_mapping = defaultdict(list)
        for original, standardized in mapping.items():
            grouped_mapping[standardized].append(original)
        
        # 保存分组映射
        with open(mapping_file, 'w', encoding='utf-8') as f:
            json.dump(grouped_mapping, f, indent=2, ensure_ascii=False)
        
        print(f"分组映射文件已保存到: {mapping_file}")

# 如果没有OpenAI API，可以使用本地聚类版本
class LocalKeyStandardizer(KeyStandardizer):
    def __init__(self):
        super().__init__()
    
    def call_llm_for_standardization(self, key_group: List[str]) -> str:
        """使用启发式方法而不是LLM"""
        return self._heuristic_standardization(key_group)

# 使用示例
def main():
    # 初始化标准化器
    # 如果需要使用OpenAI，请设置OPENAI_API_KEY环境变量或传入api_key参数
    use_openai = False  # 设置为True以使用OpenAI，False使用本地方法
    
    if use_openai:
        standardizer = KeyStandardizer()
        print("使用OpenAI进行标准化")
    else:
        standardizer = LocalKeyStandardizer()
        print("使用本地方法进行标准化")
    
    # 指定包含JSON文件的文件夹路径
    folder_path = input("请输入包含JSON文件的文件夹路径: ").strip()
    
    if not os.path.exists(folder_path):
        print(f"文件夹不存在: {folder_path}")
        return
    
    # 执行标准化
    try:
        results = standardizer.standardize_keys_from_folder(folder_path)
        
        if 'error' in results:
            print(f"错误: {results['error']}")
            return
        
        # 保存详细结果
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(folder_path, f"key_standardization_results_{timestamp}.json")
        standardizer.save_results(results, output_file)
        
        # 生成分组映射文件
        mapping_file = os.path.join(folder_path, f"key_mapping_{timestamp}.json")
        standardizer.generate_mapping_file(results, mapping_file)
        
        # 打印摘要
        print("\n" + "="*50)
        print("标准化结果摘要")
        print("="*50)
        print(f"处理的文件夹: {results['folder_processed']}")
        print(f"处理的文件数量: {results['total_files']}")
        print(f"发现的唯一key数量: {results['total_keys']}")
        print(f"形成的聚类数量: {results['total_clusters']}")
        print(f"未聚类的key数量: {results['noise_keys']}")
        
        print("\n前10个标准化映射示例:")
        for i, (orig, std) in enumerate(list(results['standardization_mapping'].items())[:10]):
            print(f"  {orig} -> {std}")
        
        print(f"\n完整结果已保存到:")
        print(f"  - 详细结果: {output_file}")
        print(f"  - 分组映射: {mapping_file}")
        
    except Exception as e:
        print(f"标准化过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
