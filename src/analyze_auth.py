import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('auth_trace.csv', names=['time', 'tcp_stream', 'h2_stream', 'method', 'status', 'path'])
df = df.dropna(how='all')

transactions = {} # Links Stream IDs to their original requested Path
req_amf_ausf = None
req_ausf_udm = None
res_udm_ausf = None
res_ausf_amf = None

print("\n=== NF SEQUENCE DIAGRAM (Authentication Phase) ===")

for index, row in df.iterrows():
    time = float(row['time'])
    tx_id = f"{row['tcp_stream']}_{row['h2_stream']}"
    method = str(row['method'])
    status = str(row['status'])
    path = str(row['path'])

    if 'POST' in method or 'GET' in method:
        transactions[tx_id] = path

        if 'nausf' in path and 'ue-authentications' in path and req_amf_ausf is None:
            print(f"[{time:.4f}] AMF ---> AUSF : Auth Request (Nausf)")
            req_amf_ausf = time
        elif 'nudm' in path and 'security-information' in path and req_ausf_udm is None:
            print(f"[{time:.4f}] AUSF ---> UDM : Auth Data Request (Nudm)")
            req_ausf_udm = time

    elif status != 'nan' and status != 'None' and status != '':
        if tx_id in transactions:
            orig_path = transactions[tx_id]

            if 'nudm' in orig_path and 'security-information' in orig_path and res_udm_ausf is None:
                print(f"[{time:.4f}] UDM ---> AUSF : Auth Data Response ({float(status):.0f})")
                res_udm_ausf = time
            elif 'nausf' in orig_path and 'ue-authentications' in orig_path and res_ausf_amf is None:
                print(f"[{time:.4f}] AUSF ---> AMF : Auth Response ({float(status):.0f})")
                res_ausf_amf = time

print("\n=== LATENCY BREAKDOWN ===")
if req_amf_ausf and req_ausf_udm and res_udm_ausf and res_ausf_amf:
    ausf_prep = (req_ausf_udm - req_amf_ausf) * 1000
    udm_proc = (res_udm_ausf - req_ausf_udm) * 1000
    ausf_fin = (res_ausf_amf - res_udm_ausf) * 1000
    total = (res_ausf_amf - req_amf_ausf) * 1000

    print(f"1. AUSF Prep Time (Request received to querying UDM): {ausf_prep:.2f} ms")
    print(f"2. UDM Processing (DB lookup & Crypto generation): {udm_proc:.2f} ms")
    print(f"3. AUSF Finalization (Validating UDM response to AMF): {ausf_fin:.2f} ms")
    print(f"-> Total Authentication Control Plane Latency: {total:.2f} ms\n")

    labels = ['AUSF Prep', 'UDM Processing', 'AUSF Finalization']
    times = [max(ausf_prep, 0.1), max(udm_proc, 0.1), max(ausf_fin, 0.1)] # Prevents invisible bars if latency is near 0

    plt.figure(figsize=(9, 5))
    bars = plt.bar(labels, times, color=['#ff9999','#66b3ff','#99ff99'], edgecolor='black')
    plt.ylabel('Latency (milliseconds)', fontweight='bold')
    plt.title('5G Registration: Microservice Latency Breakdown', fontweight='bold')

    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval + (max(times)*0.02), f"{yval:.2f} ms", ha='center', va='bottom', fontweight='bold')

    plt.tight_layout()
    plt.savefig('Authentication_Latency.png')
    print("Graph successfully saved as 'Authentication_Latency.png'")
else:
    print("Error: Incomplete flow. Please ensure the UE completed a full registration.")
