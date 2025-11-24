# 全局常量文档目录

## 📚 文档结构

本目录包含了全局常量系统的完整文档：

### 📖 核心文档

1. **[全局常量使用指南](global_constants_guide.md)**
   - 为什么使用全局常量
   - 如何导入和使用常量
   - 最佳实践和性能考虑
   - 实际代码示例

2. **[API参考文档](constants_api_reference.md)**
   - 所有常量的详细列表
   - 枚举类的方法和属性
   - 验证函数说明
   - 类型提示信息

3. **[迁移指南](constants_migration_guide.md)**
   - 从硬编码到常量的迁移步骤
   - 常见问题和解决方案
   - 自动化迁移工具
   - 代码对比示例

### 🔗 相关文档

- [项目README](../README.md) - 项目整体文档
- [时间周期使用指南](timeframe_usage.md) - 时间周期详细说明
- [项目总结](project_summary.md) - 项目概览和实现细节
- [系统设计文档](system_design.md) - 完整的架构设计

## 🎯 快速开始

### 1. 了解为什么需要常量系统

阅读[全局常量使用指南](global_constants_guide.md#为什么使用全局常量)了解常量系统的优势。

### 2. 学习基本用法

查看[全局常量使用指南](global_constants_guide.md#导入和使用)学习如何导入和使用常量。

### 3. 查看完整API

参考[API参考文档](constants_api_reference.md)了解所有可用的常量和函数。

### 4. 迁移现有代码

如果需要从硬编码迁移到常量，请阅读[迁移指南](constants_migration_guide.md)。

## 📝 文档使用说明

### 符号说明

| 符号 | 含义 |
|------|------|
| ✅ | 推荐做法 |
| ❌ | 错误做法 |
| ⚠️ | 注意事项 |
| 💡 | 技巧提示 |
| 🔗 | 相关链接 |

### 代码示例

所有文档都包含了详细的代码示例：

```python
# 示例代码总是有完整的上下文
from utils.constants import Timeframe, validate_timeframe

def example_function(interval):
    validate_timeframe(interval)
    tf = Timeframe.from_string(interval)
    print(f"处理 {tf.value} 数据 ({tf.seconds}秒)")
```

### 测试和验证

常量系统包含完整的测试覆盖：

```bash
# 运行常量相关测试
pytest tests/test_constants.py -v

# 运行特定测试
pytest tests/test_constants.py::TestTimeframeEnum -v
```

## 🔄 文档更新记录

| 版本 | 日期 | 更新内容 | 作者 |
|------|------|----------|------|
| 1.0.0 | 2024-01-01 | 初始版本，创建基础文档 | Claude |
| 1.1.0 | 2024-01-15 | 添加迁移指南和自动化工具 | Claude |
| 1.2.0 | 2024-01-20 | 完善API参考文档 | Claude |

## 🤝 贡献指南

### 添加新常量

1. 在 `utils/constants.py` 中添加常量定义
2. 添加相应的验证函数（如果需要）
3. 在 `tests/test_constants.py` 中添加测试
4. 更新此API参考文档
5. 更新使用指南中的示例

### 更新文档

1. 确保所有示例代码都可以正常运行
2. 保持文档格式一致
3. 添加必要的类型提示
4. 更新版本记录

### 报告问题

如果发现文档中的问题：

1. 检查代码示例是否正确
2. 验证API描述是否准确
3. 提交Issue或PR修复

## 🔗 外部资源

### Python官方文档
- [枚举类型](https://docs.python.org/3/library/enum.html)
- [类型提示](https://docs.python.org/3/library/typing.html)
- [Final类型](https://docs.python.org/3/library/typing.html#typing.Final)

### 相关项目
- [CCXT](https://github.com/ccxt/ccxt) - 加密货币交易库
- [Pandas](https://pandas.pydata.org/) - 数据分析库
- [Apache Parquet](https://parquet.apache.org/) - 列式存储格式

---

*最后更新：2024年1月*