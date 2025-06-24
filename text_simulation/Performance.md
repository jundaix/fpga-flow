# embedding工具与中英文相似度关系

采用embedding模型将文本转化为向量后计算testbench的余弦相似度，对相似度高于阈值的testbench代码认定为生成了和源设计代码相同的代码。
以下表格展示了使用的embedding模型、设计源代码注释语言、相似度计算结果

| 采用模型       | 异常testbench | 正常testbench | 差异值     |
|:--------------:|:--------------:|:--------------:|:----------:|
| text-embedding-3-large（中文）   | 0.889          | 0.6873         | 0.2017     |
| text-embedding-3-large（英文）   | 0.9998         | 0.7431         | 0.2567     |
| text-embedding-3-small（中文）   | 0.8111         | 0.681          | 0.1301     |
| text-embedding-3-small（英文）   | 0.9997         | 0.7109         | 0.2888     |
