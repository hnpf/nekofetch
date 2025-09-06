#!/usr/bin/env bash

# ------------------------
# nekofetch.sh - CLI system info
# ------------------------
# The MIT License (MIT)
#
# Copyright (c) 2025 @VIREX - inspiration to Dylan Araps
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# helper to print field with padding
#!/usr/bin/env bash
# nekofetch.sh - CLI system info
# MIT 2025 @VIREX
set -u
HOSTNAME_CMD=$(command -v hostname || true)
HOSTNAME=$([ -n "$HOSTNAME_CMD" ] && "$HOSTNAME_CMD" 2>/dev/null || uname -n)
HOSTNAME=$(uname -n)

# colors
RED=$(tput setaf 1 2>/dev/null || printf '\033[31m')
GREEN=$(tput setaf 2 2>/dev/null || printf '\033[32m')
YELLOW=$(tput setaf 3 2>/dev/null || printf '\033[33m')
CYAN=$(tput setaf 6 2>/dev/null || printf '\033[36m')
MAGENTA=$(tput setaf 5 2>/dev/null || printf '\033[35m')
RESET=$(tput sgr0 2>/dev/null || printf '\033[0m')

info() {
    printf "${GREEN}%-14s${RESET}: %s\n" "$1" "$2"
}

print_logo() {
    echo -e "${CYAN}░▒▓███████▓▒░░▒▓████████▓▒░▒▓█▓▒░░▒▓█▓▒░░▒▓██████▓▒░${RESET}"
    echo -e "${CYAN}░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░${RESET}"
    echo -e "${CYAN}░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░${RESET}"
    echo -e "${CYAN}░▒▓█▓▒░░▒▓█▓▒░▒▓██████▓▒░ ░▒▓███████▓▒░░▒▓█▓▒░░▒▓█▓▒░${RESET}"
    echo -e "${CYAN}░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░${RESET}"
    echo -e "${CYAN}░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░${RESET}"
    echo -e "${CYAN}░▒▓█▓▒░░▒▓█▓▒░▒▓████████▓▒░▒▓█▓▒░░▒▓█▓▒░░▒▓██████▓▒░${RESET}"
}

detect_packages() {
    if command -v pacman &>/dev/null; then
        pacman -Q 2>/dev/null | wc -l
    elif command -v dpkg &>/dev/null; then
        dpkg -l 2>/dev/null | awk '/^ii/ {count++} END{print count+0}'
    elif command -v rpm &>/dev/null; then
        rpm -qa 2>/dev/null | wc -l
    elif command -v apk &>/dev/null; then
        apk info 2>/dev/null | wc -l
    elif command -v brew &>/dev/null; then
        brew list 2>/dev/null | wc -l
    else
        echo "unknown"
    fi
}

# draw horizontal gradient bar
draw_bar() {
    local percent=$1
    local width=${2:-30}
    local fill=$((percent*width/100))
    if (( fill < 0 )); then fill=0; fi
    if (( fill > width )); then fill=width; fi
    local empty=$((width-fill))
    local bar=""
    for ((i=0;i<fill;i++)); do
        if ((i<width/3)); then
            bar+="${GREEN}█${RESET}"
        elif ((i<2*width/3)); then
            bar+="${YELLOW}█${RESET}"
        else
            bar+="${RED}█${RESET}"
        fi
    done
    for ((i=0;i<empty;i++)); do
        bar+="░"
    done
    echo -n "$bar"
}

# compute cpu usage percent using /proc/stat
get_cpu_percent() {
    local prev total_prev idle_prev cur total_cur idle_cur diff_total diff_idle usage
    read -r _ a b c d e f g h i j < <(awk '/^cpu /{for(x=2;x<=11;x++)printf "%s ",$x;print ""}' /proc/stat)
    total_prev=$((a+b+c+d+e+f+g+h+i+j))
    idle_prev=$((d+e))
    sleep 0.15
    read -r _ a b c d e f g h i j < <(awk '/^cpu /{for(x=2;x<=11;x++)printf "%s ",$x;print ""}' /proc/stat)
    total_cur=$((a+b+c+d+e+f+g+h+i+j))
    idle_cur=$((d+e))
    diff_total=$((total_cur-total_prev))
    diff_idle=$((idle_cur-idle_prev))
    if (( diff_total > 0 )); then
        usage=$(( ( (diff_total - diff_idle) * 100 / diff_total ) ))
    else
        usage=0
    fi
    printf "%d" "$usage"
}

# memory percent
get_mem_percent() {
    awk '/Mem:/ {printf "%d",($3/$2)*100}' <(free -b) 2>/dev/null || echo "0"
}

# resolution
get_resolution() {
    if command -v xrandr &>/dev/null; then
        xrandr --current 2>/dev/null | awk '/\*/{print $1; exit}' || echo "$(tput cols)x$(tput lines)"
    else
        echo "$(tput cols)x$(tput lines)"
    fi
}

# cpu model
get_cpu_model() {
    awk -F: '/model name/ {gsub(/^ +| +$/,"",$2); print $2; exit}' /proc/cpuinfo 2>/dev/null \
    || awk -F: '/Processor/ {gsub(/^ +| +$/,"",$2); print $2; exit}' /proc/cpuinfo 2>/dev/null \
    || echo "unknown"
}

# improved gpu detection
get_gpu() {
    local out=""
    if command -v lspci &>/dev/null; then
        out=$(lspci -nn | awk 'BEGIN{IGNORECASE=1} /vga|display|3d/ { $1=""; sub(/^ +/,""); print; exit }')
    fi

    [ -n "$out" ] || out="unknown"
    printf "%s" "$out"
}



# disk usage for /
get_disk() {
    df -h / 2>/dev/null | awk 'NR==2{printf "%s used of %s (%s)", $3, $2, $5}' || echo "unknown"
}

# battery
get_battery() {
    if command -v acpi &>/dev/null; then
        acpi -b 2>/dev/null | awk -F', ' '{printf "%s %s", $2, $3; exit}' || echo "unknown"
    else
        if [ -d /sys/class/power_supply ]; then
            for BAT in /sys/class/power_supply/BAT*; do
                [ -e "$BAT" ] || continue
                cap=$(cat "$BAT"/capacity 2>/dev/null)
                stat=$(cat "$BAT"/status 2>/dev/null)
                if [ -n "$cap" ]; then
                    printf "%s%% %s" "$cap" "${stat:-unknown}"
                    return
                fi
            done
        fi
        echo "N/A"
    fi
}

# gather a snapshot of info for non live mode
get_info() {
    local cpu_model gpu mem disk resolution battery
    cpu_model="$(get_cpu_model)"
    gpu="$(get_gpu)"
    mem="$(free -h | awk '/Mem:/{printf "%s (%d%%)", $3, ($3/$2)*100}')" || mem="$(get_mem_percent)%"
    disk="$(get_disk)"
    resolution="$(get_resolution)"
    battery="$(get_battery)"
    printf "%s|%s|%s|%s|%s|%s" "$cpu_model" "$gpu" "$mem" "$disk" "$resolution" "$battery"
}

print_info() {
    IFS='|' read -r cpu gpu mem disk resolution battery <<< "$(get_info)"
    print_logo
    echo -e "${YELLOW}$(whoami)@$HOSTNAME${RESET}"
    info "OS" "$(uname -s) $(uname -r)"
    info "Kernel" "$(uname -r)"
    info "Uptime" "$(uptime -p | sed -e "s/up //")"
    info "Packages" "$(detect_packages)"
    info "Shell" "${SHELL:-unknown}"
    info "Resolution" "$resolution"
    info "DE" "${XDG_CURRENT_DESKTOP:-unknown}"
    if command -v wmctrl &>/dev/null; then
        info "WM" "$(wmctrl -m 2>/dev/null | awk -F: '/Name/ {gsub(/^ +| +$/,"",$2); print $2; exit}')"
    else
        info "WM" "unknown"
    fi
    info "CPU" "$cpu"
    info "GPU" "$gpu"
    info "Memory" "$mem"
    info "Disk" "$disk"
    info "Battery" "$battery"
}

# improved live printing that doesn't stomp the header and restores cursor properly
print_info_live() {
    trap 'tput cnorm; echo; exit' INT TERM
    tput civis 2>/dev/null || true
    print_logo
    echo -e "${YELLOW}$(whoami)@$HOSTNAME${RESET}"
    info "OS" "$(uname -s) $(uname -r)"
    info "Kernel" "$(uname -r)"
    info "Uptime" "$(uptime -p | sed -e "s/up //")"
    info "Packages" "$(detect_packages)"
    info "Shell" "${SHELL:-unknown}"
    info "Resolution" "$(get_resolution)"
    info "DE" "${XDG_CURRENT_DESKTOP:-unknown}"
    if command -v wmctrl &>/dev/null; then
        info "WM" "$(wmctrl -m 2>/dev/null | awk -F: '/Name/ {gsub(/^ +| +$/,"",$2); print $2; exit}')"
    else
        info "WM" "unknown"
    fi
    echo
    # save cursor position right here then overwrite what follows on each refresh
    tput sc
    # loop
    while true; do
        cpu=$(get_cpu_percent)
        mem=$(get_mem_percent)
        tput rc
        # print two lines and pad them so previous long text is overwritten
        printf "%-120s\n" "${MAGENTA}CPU     ${RESET}: $(draw_bar "$cpu" 40) $cpu%%"
        printf "%-120s\n" "${MAGENTA}Memory  ${RESET}: $(draw_bar "$mem" 40) $mem%%"
        # small pause
        sleep 0.5
    done
}

case "${1-}" in
    --json)
        echo '{"error":"json live mode not implemented yet"}'
        ;;
    *) print_info ;;
esac