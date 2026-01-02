# GitHub Actions 深度研究报告

## 概述

GitHub Actions 是 GitHub 于 2018 年推出的 CI/CD 平台，允许开发者在仓库中直接自动化构建、测试和部署流程。到 2024 年初，该平台每天运行约 **2300 万个作业**，2025 年公共仓库免费使用了 **115 亿分钟**（约 1.84 亿美元）的 Actions。

---

## 一、核心概念与架构

### 1.1 基本组件

| 组件 | 说明 |
|------|------|
| **Workflow（工作流）** | 可配置的自动化流程，定义在 `.github/workflows/*.yml` |
| **Event（事件）** | 触发工作流的活动，如 push、pull_request |
| **Job（作业）** | 工作流中的一组步骤，运行在同一个运行器上 |
| **Step（步骤）** | 作业中的单个任务，可以是 shell 命令或 Action |
| **Action（动作）** | 可复用的独立命令单元 |
| **Runner（运行器）** | 执行工作流的服务器 |

### 1.2 工作流文件结构

```yaml
name: CI Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # 每天凌晨2点
  workflow_dispatch:  # 手动触发
    inputs:
      environment:
        description: '部署环境'
        required: true
        default: 'staging'

env:
  NODE_VERSION: '20'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
      - run: npm ci
      - run: npm test
```

---

## 二、触发器详解

### 2.1 常用触发事件

| 事件类型 | 用途 | 示例配置 |
|----------|------|----------|
| `push` | 代码推送时触发 | `branches: [main]`, `paths: ['src/**']` |
| `pull_request` | PR 创建/更新时触发 | `types: [opened, synchronize]` |
| `schedule` | 定时任务 | `cron: '0 0 * * *'` |
| `workflow_dispatch` | 手动触发 | 支持自定义输入参数 |
| `repository_dispatch` | 外部 API 触发 | 用于跨仓库或外部系统触发 |
| `release` | 发布事件 | `types: [published, created]` |
| `workflow_call` | 可复用工作流调用 | 用于工作流复用 |

### 2.2 路径过滤

```yaml
on:
  push:
    paths:
      - 'src/**'
      - '!src/**/*.test.js'  # 排除测试文件
    paths-ignore:
      - 'docs/**'
      - '*.md'
```

---

## 三、自动部署最佳实践

### 3.1 部署到云平台

#### AWS ECS 部署

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build, tag, and push image to ECR
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          ECR_REPOSITORY: my-app
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG

      - name: Deploy to ECS
        uses: aws-actions/amazon-ecs-deploy-task-definition@v1
        with:
          task-definition: task-definition.json
          service: my-service
          cluster: my-cluster
          wait-for-service-stability: true
```

#### Kubernetes 部署

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up kubectl
        uses: azure/setup-kubectl@v3
        with:
          version: 'v1.28.0'

      - name: Configure kubectl
        run: |
          echo "${{ secrets.KUBE_CONFIG }}" | base64 -d > ~/.kube/config

      - name: Deploy to Kubernetes
        run: |
          kubectl set image deployment/my-app \
            my-app=${{ secrets.REGISTRY }}/my-app:${{ github.sha }}
          kubectl rollout status deployment/my-app
```

#### SSH/rsync 部署（传统服务器）

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1.0.0
        with:
          host: ${{ secrets.HOST }}
          username: ${{ secrets.USERNAME }}
          key: ${{ secrets.SSH_KEY }}
          script: |
            cd /var/www/app
            git pull origin main
            npm install --production
            pm2 restart all
```

### 3.2 部署环境管理

```yaml
jobs:
  deploy-staging:
    runs-on: ubuntu-latest
    environment:
      name: staging
      url: https://staging.example.com
    steps:
      - run: echo "Deploying to staging..."

  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://example.com
    steps:
      - run: echo "Deploying to production..."
```

---

## 四、Secrets 与安全管理

### 4.1 Secrets 层级

| 层级 | 作用范围 | 配置位置 |
|------|----------|----------|
| **仓库级** | 单个仓库 | Settings → Secrets → Repository secrets |
| **环境级** | 特定环境 | Settings → Environments → Environment secrets |
| **组织级** | 组织内仓库 | Organization Settings → Secrets |

### 4.2 安全最佳实践

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read  # 最小权限原则
      packages: write
    steps:
      - uses: actions/checkout@v4

      # 使用 OIDC 无需存储长期凭证
      - name: Configure AWS OIDC
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789:role/GitHubActionsRole
          aws-region: us-east-1
```

### 4.3 环境保护规则

- **手动审批**：生产环境部署前需要指定审批人批准
- **等待计时器**：部署前强制等待指定时间
- **分支限制**：限制只有特定分支可以部署到该环境
- **自定义保护规则**：GitHub Enterprise 支持创建自定义规则

---

## 五、Matrix Strategy（矩阵策略）

### 5.1 基础用法

```yaml
jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        node-version: [18, 20, 22]
        exclude:
          - os: windows-latest
            node-version: 18
        include:
          - os: ubuntu-latest
            node-version: 20
            experimental: true
      fail-fast: false  # 一个失败不影响其他
      max-parallel: 4   # 最大并行数
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
      - run: npm test
```

### 5.2 动态矩阵

```yaml
jobs:
  setup:
    runs-on: ubuntu-latest
    outputs:
      matrix: ${{ steps.set-matrix.outputs.matrix }}
    steps:
      - id: set-matrix
        run: |
          echo "matrix={\"include\":[{\"project\":\"web\"},{\"project\":\"api\"}]}" >> $GITHUB_OUTPUT

  build:
    needs: setup
    runs-on: ubuntu-latest
    strategy:
      matrix: ${{ fromJSON(needs.setup.outputs.matrix) }}
    steps:
      - run: echo "Building ${{ matrix.project }}"
```

---

## 六、可复用工作流（Reusable Workflows）

### 6.1 创建可复用工作流

```yaml
# .github/workflows/reusable-deploy.yml
name: Reusable Deploy

on:
  workflow_call:
    inputs:
      environment:
        required: true
        type: string
      image-tag:
        required: true
        type: string
    secrets:
      DEPLOY_KEY:
        required: true
    outputs:
      deploy-url:
        description: "Deployment URL"
        value: ${{ jobs.deploy.outputs.url }}

jobs:
  deploy:
    runs-on: ubuntu-latest
    outputs:
      url: ${{ steps.deploy.outputs.url }}
    steps:
      - name: Deploy
        id: deploy
        run: |
          echo "Deploying to ${{ inputs.environment }}"
          echo "url=https://${{ inputs.environment }}.example.com" >> $GITHUB_OUTPUT
```

### 6.2 调用可复用工作流

```yaml
jobs:
  deploy-staging:
    uses: ./.github/workflows/reusable-deploy.yml
    with:
      environment: staging
      image-tag: ${{ github.sha }}
    secrets:
      DEPLOY_KEY: ${{ secrets.STAGING_DEPLOY_KEY }}

  deploy-production:
    needs: deploy-staging
    uses: ./.github/workflows/reusable-deploy.yml
    with:
      environment: production
      image-tag: ${{ github.sha }}
    secrets:
      DEPLOY_KEY: ${{ secrets.PROD_DEPLOY_KEY }}
```

### 6.3 限制与注意事项

- 单个工作流最多调用 **20 个**可复用工作流
- 可复用工作流最多嵌套 **4 层**
- 环境变量不会在调用者和被调用者之间自动传递，需使用 outputs
- 传递矩阵参数时使用 JSON 字符串 + `fromJSON()`

---

## 七、缓存与构建优化

### 7.1 actions/cache 使用

```yaml
- name: Cache node modules
  uses: actions/cache@v4
  with:
    path: ~/.npm
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
    restore-keys: |
      ${{ runner.os }}-node-

- name: Cache Gradle packages
  uses: actions/cache@v4
  with:
    path: |
      ~/.gradle/caches
      ~/.gradle/wrapper
    key: ${{ runner.os }}-gradle-${{ hashFiles('**/*.gradle*', '**/gradle-wrapper.properties') }}
```

### 7.2 setup-* Actions 内置缓存

```yaml
# Node.js - 自动缓存
- uses: actions/setup-node@v4
  with:
    node-version: '20'
    cache: 'npm'  # 或 'yarn', 'pnpm'

# Python - 自动缓存
- uses: actions/setup-python@v5
  with:
    python-version: '3.12'
    cache: 'pip'
```

### 7.3 缓存策略对比

| 策略 | 适用场景 | 缓存大小限制 |
|------|----------|--------------|
| **actions/cache** | 依赖缓存、构建缓存 | 单仓库 10GB |
| **setup-* 内置缓存** | 语言依赖 | 同上 |
| **Docker layer 缓存** | 容器构建 | 需配合 buildx |
| **Artifacts** | 跨 Job 传递 | 90 天保留 |

---

## 八、并发控制

### 8.1 Concurrency 配置

```yaml
# 工作流级别
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

# 作业级别
jobs:
  deploy:
    concurrency:
      group: production
      cancel-in-progress: false  # 生产环境不取消进行中的部署
```

### 8.2 部署队列管理

```yaml
concurrency:
  group: deploy-${{ github.ref }}
  cancel-in-progress: false
# 效果：最多一个正在运行 + 一个待处理的部署
```

---

## 九、自托管运行器（Self-hosted Runners）

### 9.1 适用场景

| 场景 | 推荐方案 |
|------|----------|
| 公共仓库、标准环境 | GitHub 托管运行器 |
| 私有网络访问 | 自托管运行器 |
| 特殊硬件（GPU、ARM） | 自托管运行器 |
| 合规要求（数据本地化） | 自托管运行器 |
| 高并发需求 | 自托管 + ARC 自动扩展 |

### 9.2 配置层级

```
企业级运行器
  └── 组织级运行器
       └── 仓库级运行器
```

### 9.3 安全最佳实践

1. **使用临时运行器（Ephemeral）**：每个作业使用干净环境，降低跨作业攻击风险
2. **运行器组隔离**：将运行器分组，限制特定仓库/工作流访问
3. **不在公共仓库使用自托管运行器**：防止恶意 PR 执行任意代码
4. **定期轮换令牌**：配置令牌 1 小时过期

### 9.4 Kubernetes 自动扩展 (ARC)

```yaml
# actions-runner-controller 配置示例
apiVersion: actions.summerwind.dev/v1alpha1
kind: RunnerDeployment
metadata:
  name: example-runner
spec:
  replicas: 3
  template:
    spec:
      repository: owner/repo
      labels:
        - self-hosted
        - linux
        - x64
```

---

## 十、自定义 Action 开发

### 10.1 Action 类型对比

| 类型 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| **JavaScript** | 启动快、跨平台 | 需要打包依赖 | 通用工具 |
| **Docker** | 环境一致、隔离性好 | 启动慢、仅 Linux | 复杂依赖 |
| **Composite** | 无需打包、易维护 | 功能受限 | 步骤编排 |

### 10.2 Composite Action 示例

```yaml
# .github/actions/setup-project/action.yml
name: 'Setup Project'
description: 'Setup Node.js and install dependencies'

inputs:
  node-version:
    description: 'Node.js version'
    required: false
    default: '20'

runs:
  using: 'composite'
  steps:
    - uses: actions/setup-node@v4
      with:
        node-version: ${{ inputs.node-version }}
        cache: 'npm'

    - run: npm ci
      shell: bash

    - run: npm run build
      shell: bash
```

### 10.3 JavaScript Action 结构

```
my-action/
├── action.yml
├── dist/
│   └── index.js      # 打包后的代码
├── src/
│   └── index.js      # 源代码
├── package.json
└── README.md
```

```javascript
// src/index.js
const core = require('@actions/core');
const github = require('@actions/github');

async function run() {
  try {
    const name = core.getInput('name');
    console.log(`Hello ${name}!`);

    const payload = github.context.payload;
    core.setOutput('sha', payload.after);
  } catch (error) {
    core.setFailed(error.message);
  }
}

run();
```

---

## 十一、常用官方 Actions

| Action | 用途 | 示例 |
|--------|------|------|
| `actions/checkout@v4` | 检出代码 | 几乎所有工作流必用 |
| `actions/setup-node@v4` | 配置 Node.js | 支持缓存 |
| `actions/setup-python@v5` | 配置 Python | 支持缓存 |
| `actions/cache@v4` | 依赖缓存 | 加速构建 |
| `actions/upload-artifact@v4` | 上传产物 | 跨 Job 传递 |
| `actions/download-artifact@v4` | 下载产物 | 跨 Job 传递 |
| `actions/github-script@v7` | 执行 GitHub API | 自动化 Issue/PR |
| `docker/build-push-action@v5` | 构建推送镜像 | 容器化部署 |

---

## 十二、调试与故障排查

### 12.1 启用调试日志

```yaml
# 仓库 Secrets 中设置
ACTIONS_STEP_DEBUG: true
ACTIONS_RUNNER_DEBUG: true
```

### 12.2 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 缓存未命中 | key 变化或过期 | 检查 hashFiles 路径 |
| 权限拒绝 | GITHUB_TOKEN 权限不足 | 配置 permissions |
| 超时失败 | 作业超过 6 小时 | 拆分作业或优化 |
| 并发冲突 | 同一 concurrency group | 调整 cancel-in-progress |

---

## 十三、定价与限制

### 13.1 免费额度（2025年）

| 账户类型 | 每月分钟数 | 存储 |
|----------|------------|------|
| Free | 2,000 | 500 MB |
| Pro | 3,000 | 1 GB |
| Team | 3,000 | 2 GB |
| Enterprise | 50,000 | 50 GB |

> **公共仓库完全免费**，2025年免费使用了 115 亿分钟

### 13.2 运行器分钟倍率

| 运行器 | 倍率 |
|--------|------|
| Linux | 1x |
| Windows | 2x |
| macOS | 10x |

---

## 十四、2024-2025 新特性

1. **Deployment Protection Rules**：自定义部署保护规则（Enterprise）
2. **Larger Runners**：更大规格托管运行器（最高 64 核）
3. **GPU Runners**：支持 GPU 运行器（Beta）
4. **Immutable Actions**：不可变 Actions 提升安全性
5. **Required Workflows**：组织级强制工作流
6. **Artifact Attestations**：工件签名认证

---

## 参考资源

- [GitHub Actions 官方文档](https://docs.github.com/en/actions)
- [GitHub Actions Marketplace](https://github.com/marketplace?type=actions)
- [actions/cache 官方仓库](https://github.com/actions/cache)
- [Reusable Workflows 教程](https://github.com/skills/reusable-workflows)
- [Self-hosted Runners 指南](https://docs.github.com/en/actions/hosting-your-own-runners)
- [Deployment Protection Rules 公告](https://github.blog/news-insights/product-news/announcing-github-actions-deployment-protection-rules-now-in-public-beta/)

---

*报告生成时间：2025年1月2日*
