#!/bin/bash
set -e 

# ==============================================================================
# 阶段 0: 容器持久化逻辑
# ==============================================================================
CONTAINER_NAME="wwsearch_env"
ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)

echo "--- 阶段 0: 检查容器状态 ---"
if [ "$(sudo docker ps -aq -f name=^/${CONTAINER_NAME}$)" ]; then
    if [ "$(sudo docker ps -aq -f status=exited -f name=^/${CONTAINER_NAME}$)" ]; then
        echo "容器已存在但处于停止状态，正在启动..."
        sudo docker start ${CONTAINER_NAME}
    else
        echo "容器正在运行中，无需重启。"
    fi
else
    echo "容器不存在，正在创建新容器..."
    sudo docker run -d --name ${CONTAINER_NAME} -v "$ROOT_DIR":/work -w /work ubuntu:18.04 sleep infinity
fi

docker_exec="sudo docker exec ${CONTAINER_NAME}"

# ==============================================================================
# 第一阶段: 环境增量更新
# ==============================================================================
echo "--- 第一阶段: 检查并安装必要依赖 ---"
if ! $docker_exec which wget > /dev/null 2>&1; then
    echo "正在初始化容器环境..."
    $docker_exec apt-get update
    $docker_exec apt-get install -y build-essential vim curl wget psmisc python3
    $docker_exec bash -c "echo '/work/phxrpc/third_party/protobuf/lib' > /etc/ld.so.conf.d/protobuf.conf && ldconfig"
    # 注入动态库路径并刷新
    $docker_exec bash -c "echo '/work/phxrpc/third_party/protobuf/lib' > /etc/ld.so.conf.d/protobuf.conf && ldconfig"
else
    echo "容器环境依赖已就绪。"
fi

# ==============================================================================
# 第二阶段: 框架编译 (智能跳过)
# ==============================================================================
echo "--- 第二阶段: 框架编译 ---"

THIRD_PARTY_DIR="$ROOT_DIR/phxrpc/third_party"
PROTO_TGZ="$THIRD_PARTY_DIR/protobuf-cpp-3.0.0.tar.gz"
PROTO_DIR="$THIRD_PARTY_DIR/protobuf"

# 逻辑：如果存在编译后的文件夹，直接跳过下载
if [ -d "$PROTO_DIR" ] && [ -f "$PROTO_DIR/bin/protoc" ]; then
    echo "检测到编译好的 Protobuf 目录，跳过下载与框架重编。"
else
    echo "未检测到完整的 Protobuf 环境，准备编译..."
    
    # 如果连压缩包也没有，才尝试下载
    if [ ! -f "$PROTO_TGZ" ]; then
        echo "正在下载 Protobuf 源码包..."
        curl -L -o "$PROTO_TGZ" https://github.com/google/protobuf/releases/download/v3.0.0/protobuf-cpp-3.0.0.tar.gz
    fi

    $docker_exec chmod +x phxrpc/build.sh
    $docker_exec bash -c "cd phxrpc && ./build.sh"
fi

# 确保 codegen 总是最新的
$docker_exec bash -c "cd phxrpc/codegen && make -j$(nproc)"
# ==============================================================================
# 第三阶段: Sample 逻辑注入
# ==============================================================================
echo "--- 第三阶段: Sample 逻辑注入 ---"

# 定义公共的包含路径参数
PROTO_PATH="-I . -I /work/phxrpc -I /work/phxrpc/third_party/protobuf/include"

# 1. 运行原有的 regen.sh
$docker_exec bash -c "export PHXRPC_ROOT=/work/phxrpc && \
                      export LD_LIBRARY_PATH=/work/phxrpc/third_party/protobuf/lib && \
                      cd phxrpc/sample && \
                      chmod +x regen.sh && \
                      ./regen.sh"

$docker_exec bash -c "export LD_LIBRARY_PATH=/work/phxrpc/third_party/protobuf/lib && \
                      cd phxrpc/sample && \
                      # 生成服务端逻辑模板 (search_service_impl.cpp 等)
                      ../codegen/phxrpc_pb2service -f search.proto -d . $PROTO_PATH && \
                      # 生成客户端工具模板 (search_client.conf 等)
                      ../codegen/phxrpc_pb2client -f search.proto -d . $PROTO_PATH"

# 3. 注入逻辑
echo "正在注入逻辑到 phxrpc/sample/search_service_impl.cpp..."
$docker_exec sed -i '/int SearchServiceImpl::Search/,/}/c\int SearchServiceImpl::Search(const search::SearchRequest \&req, search::SearchResult *resp) {\n    search::Site *site = resp->add_sites();\n    site->set_url("https://www.tencent.com");\n    site->set_title("Success Reconstruction");\n    return 0;\n}' phxrpc/sample/search_service_impl.cpp

$docker_exec sed -i 's/Port = 16161/Port = 16162/g' phxrpc/sample/search_server.conf
$docker_exec sed -i 's/Port = 16161/Port = 16162/g' phxrpc/sample/search_client.conf
# --- 第四阶段: 编译与启动 ---
echo "--- 第四阶段: 编译与启动 ---"

# 核心修正：在 make 前注入环境变量，确保 phxrpc_pb2tool 能运行
$docker_exec bash -c "export LD_LIBRARY_PATH=/work/phxrpc/third_party/protobuf/lib && \
                      cd phxrpc/sample && \
                      make clean && \
                      make -j$(nproc)"
# 杀掉旧进程
$docker_exec pkill -9 search_main || true

# 启动服务端
sudo docker exec -d ${CONTAINER_NAME} bash -c "export LD_LIBRARY_PATH=/work/phxrpc/third_party/protobuf/lib && cd /work/phxrpc/sample && ./search_main -c search_server.conf"

sleep 1

echo "--- 最终验证 ---"
$docker_exec bash -c "export LD_LIBRARY_PATH=/work/phxrpc/third_party/protobuf/lib && cd /work/phxrpc/sample && ./search_tool_main -c search_client.conf -f PHXEcho -s 'Reconstruction_Success'"

echo "===================================================="
echo "状态: OK"
echo "容器: ${CONTAINER_NAME} (已保持运行)"
echo "===================================================="