# 强隔离评测沙箱。被测 AI 代码不可信，生产环境应在容器内运行。
# 构建:  docker build -t ai-benchmark-sandbox -f eval/Dockerfile .
# 运行:  docker run --rm --network none --memory 512m --cpus 1 \
#           --pids-limit 128 --read-only --tmpfs /tmp \
#           -v "$PWD:/work:ro" ai-benchmark-sandbox \
#           python submit.py p001 reference/p001/solution.py --show-hidden
FROM python:3.12-slim

# 多语言运行时（按需增删）
RUN apt-get update && apt-get install -y --no-install-recommends \
        nodejs ruby \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pyyaml

# 以非 root 用户运行，降低逃逸影响
RUN useradd -m runner
USER runner
WORKDIR /work

# 关键隔离开关（由 docker run 传入，此处仅作文档）：
#   --network none     断网，防止外联/数据外泄
#   --read-only        根文件系统只读
#   --tmpfs /tmp       仅 /tmp 可写
#   --memory / --cpus  资源上限
#   --pids-limit       防 fork 炸弹
ENTRYPOINT []
