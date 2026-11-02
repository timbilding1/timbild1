FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    curl wget git nmap netcat-openbsd unzip \
    gcc build-essential libssl-dev libpcap-dev \
    perl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN pip install --no-cache-dir \
    sqlmap dirsearch wafw00f python-whois \
    dnspython paramiko impacket arjun

# gobuster
RUN GB_VER=$(curl -s https://api.github.com/repos/OJ/gobuster/releases/latest | grep '"tag_name"' | cut -d'"' -f4) && \
    wget -q "https://github.com/OJ/gobuster/releases/download/${GB_VER}/gobuster_Linux_x86_64.tar.gz" -O /tmp/gb.tar.gz && \
    tar -xzf /tmp/gb.tar.gz -C /usr/local/bin/ gobuster && chmod +x /usr/local/bin/gobuster && rm /tmp/gb.tar.gz || true

# ffuf
RUN FFUF_VER=$(curl -s https://api.github.com/repos/ffuf/ffuf/releases/latest | grep '"tag_name"' | cut -d'"' -f4) && \
    wget -q "https://github.com/ffuf/ffuf/releases/download/${FFUF_VER}/ffuf_${FFUF_VER#v}_linux_amd64.tar.gz" -O /tmp/ffuf.tar.gz && \
    tar -xzf /tmp/ffuf.tar.gz ffuf -C /usr/local/bin/ && chmod +x /usr/local/bin/ffuf && rm /tmp/ffuf.tar.gz || true

# nuclei
RUN NUC_VER=$(curl -s https://api.github.com/repos/projectdiscovery/nuclei/releases/latest | grep '"tag_name"' | cut -d'"' -f4) && \
    wget -q "https://github.com/projectdiscovery/nuclei/releases/download/${NUC_VER}/nuclei_${NUC_VER#v}_linux_amd64.zip" -O /tmp/nuc.zip && \
    unzip -q /tmp/nuc.zip nuclei -d /usr/local/bin/ && chmod +x /usr/local/bin/nuclei && rm /tmp/nuc.zip || true

# subfinder
RUN SF_VER=$(curl -s https://api.github.com/repos/projectdiscovery/subfinder/releases/latest | grep '"tag_name"' | cut -d'"' -f4) && \
    wget -q "https://github.com/projectdiscovery/subfinder/releases/download/${SF_VER}/subfinder_${SF_VER#v}_linux_amd64.zip" -O /tmp/sf.zip && \
    unzip -q /tmp/sf.zip subfinder -d /usr/local/bin/ && chmod +x /usr/local/bin/subfinder && rm /tmp/sf.zip || true

# httpx
RUN HX_VER=$(curl -s https://api.github.com/repos/projectdiscovery/httpx/releases/latest | grep '"tag_name"' | cut -d'"' -f4) && \
    wget -q "https://github.com/projectdiscovery/httpx/releases/download/${HX_VER}/httpx_${HX_VER#v}_linux_amd64.zip" -O /tmp/hx.zip && \
    unzip -q /tmp/hx.zip httpx -d /usr/local/bin/ && chmod +x /usr/local/bin/httpx && rm /tmp/hx.zip || true

# feroxbuster
RUN FB_VER=$(curl -s https://api.github.com/repos/epi052/feroxbuster/releases/latest | grep '"tag_name"' | cut -d'"' -f4) && \
    wget -q "https://github.com/epi052/feroxbuster/releases/download/${FB_VER}/feroxbuster-linux-amd64.tar.gz" -O /tmp/fb.tar.gz && \
    tar -xzf /tmp/fb.tar.gz -C /usr/local/bin/ feroxbuster && chmod +x /usr/local/bin/feroxbuster && rm /tmp/fb.tar.gz || true

# dalfox
RUN DF_VER=$(curl -s https://api.github.com/repos/hahwul/dalfox/releases/latest | grep '"tag_name"' | cut -d'"' -f4) && \
    wget -q "https://github.com/hahwul/dalfox/releases/download/${DF_VER}/dalfox_linux_amd64.tar.gz" -O /tmp/df.tar.gz && \
    tar -xzf /tmp/df.tar.gz -C /usr/local/bin/ dalfox && chmod +x /usr/local/bin/dalfox && rm /tmp/df.tar.gz || true

# katana
RUN KT_VER=$(curl -s https://api.github.com/repos/projectdiscovery/katana/releases/latest | grep '"tag_name"' | cut -d'"' -f4) && \
    wget -q "https://github.com/projectdiscovery/katana/releases/download/${KT_VER}/katana_${KT_VER#v}_linux_amd64.zip" -O /tmp/kt.zip && \
    unzip -q /tmp/kt.zip katana -d /usr/local/bin/ && chmod +x /usr/local/bin/katana && rm /tmp/kt.zip || true

RUN nuclei -update-templates -silent || true

COPY . .
RUN mkdir -p workspace
EXPOSE 8000
CMD ["python", "main.py"]

