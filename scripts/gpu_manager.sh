#!/bin/bash
# GPU resource manager for macOS
#   Pauses Ollama GPU processes when Blender is running,
#   resumes when Blender closes.
#
# Usage:
#   ./scripts/gpu_manager.sh              # monitor mode (daemon)
#   ./scripts/gpu_manager.sh --once       # single check
#   ./scripts/gpu_manager.sh stop         # kill running monitor

MONITOR_PIDFILE="/tmp/opencode_gpu_monitor.pid"
OLLAMA_PIDFILE="$HOME/.ollama/ollama.pid"
POLL_SECONDS=5

set_env_limits() {
    export OLLAMA_NUM_PARALLEL=1
    export OLLAMA_MAX_LOADED_MODELS=1
    export OLLAMA_KEEP_ALIVE=5m
    echo "[gpu] Ollama limits: parallel=1, max_loaded=1, keep_alive=5m"
}

pause_ollama() {
    if [ -f "$OLLAMA_PIDFILE" ]; then
        local pid=$(cat "$OLLAMA_PIDFILE" 2>/dev/null)
        [ -n "$pid" ] && kill -STOP "$pid" 2>/dev/null && echo "[gpu] Ollama paused (SIGSTOP)"
    fi
    # Also pause any ollama_llama_server processes
    for spid in $(pgrep -f ollama_llama_server 2>/dev/null); do
        kill -STOP "$spid" 2>/dev/null
    done
}

resume_ollama() {
    if [ -f "$OLLAMA_PIDFILE" ]; then
        local pid=$(cat "$OLLAMA_PIDFILE" 2>/dev/null)
        [ -n "$pid" ] && kill -CONT "$pid" 2>/dev/null && echo "[gpu] Ollama resumed (SIGCONT)"
    fi
    for spid in $(pgrep -f ollama_llama_server 2>/dev/null); do
        kill -CONT "$spid" 2>/dev/null
    done
}

blender_running() {
    pgrep -q -i "blender" 2>/dev/null
}

monitor_loop() {
    echo "$$" > "$MONITOR_PIDFILE"
    local was_paused=false
    echo "[gpu] Monitor started (pid $$), polling every ${POLL_SECONDS}s"

    while true; do
        if blender_running; then
            if [ "$was_paused" = false ]; then
                echo "[gpu] Blender detected — pausing Ollama"
                pause_ollama
                was_paused=true
            fi
        else
            if [ "$was_paused" = true ]; then
                echo "[gpu] Blender gone — resuming Ollama"
                resume_ollama
                was_paused=false
            fi
        fi
        sleep "$POLL_SECONDS"
    done
}

case "${1:-monitor}" in
    --once)
        set_env_limits
        if blender_running; then
            echo "[gpu] Blender is running"
            pause_ollama
        else
            echo "[gpu] Blender not running"
            resume_ollama
        fi
        ;;
    stop)
        if [ -f "$MONITOR_PIDFILE" ]; then
            pid=$(cat "$MONITOR_PIDFILE")
            kill "$pid" 2>/dev/null && echo "[gpu] Monitor (pid $pid) stopped" || echo "[gpu] No monitor running"
            rm -f "$MONITOR_PIDFILE"
        else
            echo "[gpu] No monitor PID file found"
        fi
        resume_ollama
        ;;
    monitor|*)
        set_env_limits
        monitor_loop
        ;;
esac
