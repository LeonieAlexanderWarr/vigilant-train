import pandas as pd
from pathlib import Path

REPORT_DIR = Path('Sage50Reports')

EXPECTED_FILES = {
    'AR Summary': 'CustomerAgedSummary.xlsx',
    'Customer Sales': 'CustomerSalesReport.xlsx',
    'Income Statement': 'Incumstatemtenttnt.xlsx',
    'AP Summary': 'VendorAgedSummary.xlsx',
    'Balance Sheet': 'BALANCESHEEPS.xlsx'
}

HAIRCUTS = {
    'Current': 0.02,
    '31 to 60': 0.10,
    '61 to 90': 0.30,
    '91+': 0.75
}


def verify_and_get_paths():
    if not REPORT_DIR.exists():
        print(f"Error: Directory '{REPORT_DIR}' not found.")
        return None

    missing_files = []
    file_paths = {}

    for label, filename in EXPECTED_FILES.items():
        filepath = REPORT_DIR / filename
        if filepath.exists():
            file_paths[label] = filepath
        else:
            missing_files.append(filename)

    if missing_files:
        print(f"Verification failed. Missing files: {', '.join(missing_files)}")
        return None
    
    return file_paths


def run_financial_stress_test(paths):
    # 1. Accounts Receivable & AFDA
    try:
        df_ar = pd.read_excel(paths['AR Summary'], skiprows=3)
        df_ar.columns = df_ar.columns.str.strip()
        
        ar_totals = df_ar[df_ar['Unnamed: 0'] == 'Total outstanding:'].iloc[-1]
        
        current_ar = float(ar_totals['Current'])
        ar_31_60 = float(ar_totals['31 to 60'])
        ar_61_90 = float(ar_totals['61 to 90'])
        ar_91_plus = float(ar_totals['91+'])
        
        total_ar = current_ar + ar_31_60 + ar_61_90 + ar_91_plus
        
        afda_provision = (
            (current_ar * HAIRCUTS['Current']) +
            (ar_31_60 * HAIRCUTS['31 to 60']) +
            (ar_61_90 * HAIRCUTS['61 to 90']) +
            (ar_91_plus * HAIRCUTS['91+'])
        )
        
        net_ar = total_ar - afda_provision
        
        print("--- 1. Accounts Receivable & AFDA ---")
        print(f"Total AR:           ${total_ar:,.2f}")
        print(f"Required AFDA:      ${afda_provision:,.2f}")
        print(f"Net Collectible AR: ${net_ar:,.2f}\n")
        
    except Exception as e:
        print(f"Error calculating AFDA: {e}")
        net_ar = 0

    # 2. Customer Concentration
    try:
        df_sales = pd.read_excel(paths['Customer Sales'], skiprows=3)
        customer_sales = {}
        current_cust = None
        
        for _, row in df_sales.iterrows():
            col0 = row['Unnamed: 0']
            
            if pd.notna(col0) and isinstance(col0, str):
                current_cust = str(col0).strip()
                
            if pd.isna(col0) and pd.isna(row['Date']) and pd.notna(row['Revenue']):
                if current_cust:
                    customer_sales[current_cust] = customer_sales.get(current_cust, 0) + float(row['Revenue'])

        total_sales = sum(customer_sales.values())
        
        print("--- 2. Customer Concentration ---")
        if total_sales > 0:
            found_risk = False
            for cust, sales in customer_sales.items():
                concentration = sales / total_sales
                if concentration >= 0.20:
                    found_risk = True
                    print(f"WARNING: {cust} represents {concentration*100:.1f}% of Sales (${sales:,.2f})")
            
            if not found_risk:
                print("No customers exceed 20% concentration threshold.")
        print("")
        
    except Exception as e:
        print(f"Error calculating concentration: {e}\n")

    # 3. Liquidity & Cash Runway
    try:
        df_bs = pd.read_excel(paths['Balance Sheet'])
        cash_balance = float(df_bs[df_bs.iloc[:, 0] == 'Total Cash'].iloc[0, 2])
        
        df_is = pd.read_excel(paths['Income Statement'])
        monthly_burn = float(df_is[df_is.iloc[:, 0] == 'TOTAL EXPENSE'].iloc[0, 2])
        
        df_ap = pd.read_excel(paths['AP Summary'], skiprows=3)
        df_ap.columns = df_ap.columns.str.strip()
        ap_obligations = float(df_ap[df_ap['Unnamed: 0'] == 'Total outstanding:'].iloc[-1]['Total'])
        
        numerator = cash_balance + net_ar
        denominator = monthly_burn + ap_obligations
        
        runway_months = numerator / denominator if denominator > 0 else float('inf')
        
        print("--- 3. Liquidity & Cash Runway ---")
        print(f"Cash Available:     ${cash_balance:,.2f}")
        print(f"Net AR:             ${net_ar:,.2f}")
        print(f"AP Obligations:     ${ap_obligations:,.2f}")
        print(f"Monthly Burn Rate:  ${monthly_burn:,.2f}")
        
        if runway_months > 3.0:
            print(f"Status: LOW RISK ({runway_months:.1f} months runway)\n")
        elif runway_months >= 1.0:
            print(f"Status: MODERATE RISK ({runway_months:.1f} months runway)\n")
        else:
            print(f"Status: HIGH RISK ({runway_months:.1f} months runway)\n")

    except Exception as e:
        print(f"Error calculating cash runway: {e}\n")


if __name__ == "__main__":
    report_paths = verify_and_get_paths()
    if report_paths:
        run_financial_stress_test(report_paths)