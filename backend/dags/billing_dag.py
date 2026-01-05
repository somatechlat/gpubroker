from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'gpubroker',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'billing_settlement_daily',
    default_args=default_args,
    description='Daily Billing Settlement for GPU Usage',
    schedule_interval=timedelta(days=1),
)

def calculate_costs():
    print("Calculating costs for all active tenants...")
    # SQL logic or API call to Backend would go here

def generate_invoices():
    print("Generating PDF invoices and Stripe charges...")

t1 = PythonOperator(
    task_id='calculate_costs',
    python_callable=calculate_costs,
    dag=dag,
)

t2 = PythonOperator(
    task_id='generate_invoices',
    python_callable=generate_invoices,
    dag=dag,
)

t1 >> t2
