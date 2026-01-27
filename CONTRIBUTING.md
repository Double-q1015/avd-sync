# 贡献指南

感谢您对 AVD Sync 项目的关注！我们欢迎所有形式的贡献。

## 如何贡献

### 报告问题

如果您发现了bug或有功能建议，请：

1. 检查 [Issues](https://github.com/your-username/avd-sync/issues) 中是否已有相关问题
2. 如果没有，请创建新的 Issue，包含：
   - 清晰的问题描述
   - 复现步骤（如果是bug）
   - 预期行为 vs 实际行为
   - 环境信息（Python版本、操作系统等）
   - 相关日志或错误信息

### 提交代码

1. **Fork 项目**
   ```bash
   # Fork 项目到你的 GitHub 账户
   ```

2. **克隆你的 Fork**
   ```bash
   git clone https://github.com/your-username/avd-sync.git
   cd avd-sync
   ```

3. **创建分支**
   ```bash
   git checkout -b feature/your-feature-name
   # 或
   git checkout -b fix/your-bug-fix
   ```

4. **开发**
   - 遵循项目的代码风格
   - 添加必要的注释和文档
   - 确保代码通过 lint 检查
   - 添加测试（如果适用）

5. **提交更改**
   ```bash
   git add .
   git commit -m "feat: 添加新功能描述"
   # 或
   git commit -m "fix: 修复bug描述"
   ```

6. **推送并创建 Pull Request**
   ```bash
   git push origin feature/your-feature-name
   ```
   然后在 GitHub 上创建 Pull Request

## 代码规范

### Python 代码风格

- 遵循 [PEP 8](https://www.python.org/dev/peps/pep-0008/) 代码风格
- 使用类型提示（Type Hints）
- 函数和类需要添加文档字符串（docstring）
- 行长度不超过 100 字符（如果可能）

### 提交信息规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式：

- `feat`: 新功能
- `fix`: 修复bug
- `docs`: 文档更新
- `style`: 代码格式调整（不影响功能）
- `refactor`: 代码重构
- `perf`: 性能优化
- `test`: 测试相关
- `chore`: 构建/工具链相关

示例：
```
feat: 添加并发爬取功能
fix: 修复数据库连接池问题
docs: 更新README中的使用示例
```

### 代码结构

- 保持模块化设计
- 单一职责原则
- 添加适当的错误处理
- 使用日志而不是 print

## 开发环境设置

1. **克隆项目**
   ```bash
   git clone https://github.com/your-username/avd-sync.git
   cd avd-sync
   ```

2. **创建虚拟环境**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

4. **运行测试**（如果有）
   ```bash
   # 待添加测试框架
   ```

## Pull Request 流程

1. **确保代码质量**
   - 代码通过 lint 检查
   - 没有引入新的警告
   - 遵循项目代码风格

2. **更新文档**
   - 如果添加了新功能，更新 README.md
   - 更新相关的文档文件
   - 添加代码注释

3. **测试**
   - 确保你的更改不会破坏现有功能
   - 如果可能，添加测试用例

4. **创建 Pull Request**
   - 提供清晰的 PR 描述
   - 说明更改的原因和影响
   - 关联相关的 Issue（如果有）

5. **代码审查**
   - 维护者会审查你的代码
   - 根据反馈进行修改
   - 保持耐心和礼貌

## 贡献领域

我们欢迎以下方面的贡献：

### 功能开发
- 新功能建议和实现
- 性能优化
- 错误处理和稳定性改进

### 文档改进
- 完善 README
- 添加使用示例
- 改进代码注释
- 翻译文档

### Bug 修复
- 报告和修复 bug
- 改进错误处理
- 修复兼容性问题

### 测试
- 添加单元测试
- 添加集成测试
- 提高测试覆盖率

### 工具和脚本
- 开发辅助工具
- 改进部署脚本
- 添加监控工具

## 行为准则

请遵守我们的 [行为准则](CODE_OF_CONDUCT.md)：

- 尊重所有贡献者
- 接受建设性批评
- 专注于对项目最有利的事情
- 对其他社区成员表示同理心

## 问题反馈

如果您有任何问题或需要帮助，可以：

- 创建 [Issue](https://github.com/your-username/avd-sync/issues)
- 查看现有文档
- 联系维护者

## 致谢

感谢所有为这个项目做出贡献的开发者！

您的贡献使这个项目变得更好。🎉

