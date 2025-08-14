import csv
from datetime import datetime
import random
import string

# CSV Setup
CSV_FILE = "incident_reports.csv"
HEADERS = ["reference", "phone_number", "category", "location", "severity", "description", "timestamp"]

# Initialize CSV file
def init_csv():
    with open(CSV_FILE, mode='a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=HEADERS)
        if file.tell() == 0:  # Write headers only if file is empty
            writer.writeheader()

# Generate reference number
def generate_reference():
    date_str = datetime.now().strftime("%Y%m%d")
    rand_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"INC-{date_str}-{rand_str}"

# USSD Flow
def run_ussd_flow():
    print("\n=== USSD Incident Reporting ===")
    phone_number = input("Enter your phone number: ")
    
    while True:
        print("\nMain Menu:")
        print("1. Report New Incident")
        print("2. View Previous Reports")
        print("3. Exit")
        
        choice = input("Select option (1-3): ")
        
        if choice == "1":
            report_incident(phone_number)
        elif choice == "2":
            view_reports(phone_number)
        elif choice == "3":
            print("Thank you. Stay safe!")
            break
        else:
            print("Invalid option. Please try again.")

def report_incident(phone_number):
    print("\n=== New Incident Report ===")
    
    # Category selection
    categories = {
        "1": "Theft/Burglary",
        "2": "Fire Hazard",
        "3": "Accident",
        "4": "Harassment",
        "5": "Infrastructure Damage",
        "6": "Public Health Concern"
    }
    
    print("Select Category:")
    for num, category in categories.items():
        print(f"{num}. {category}")
    category_choice = input("Enter category number (1-6): ")
    category = categories.get(category_choice, "Unknown")
    
    # Location
    location = input("Enter location (e.g., Building A, Room 101): ")
    
    # Severity
    severities = {
        "1": "Low",
        "2": "Medium",
        "3": "High",
        "4": "Emergency"
    }
    print("Select Severity:")
    for num, severity in severities.items():
        print(f"{num}. {severity}")
    severity_choice = input("Enter severity number (1-4): ")
    severity = severities.get(severity_choice, "Unknown")
    
    # Description
    description = input("Briefly describe the incident: ")
    
    # Confirmation
    print("\nPlease confirm:")
    print(f"Category: {category}")
    print(f"Location: {location}")
    print(f"Severity: {severity}")
    print(f"Description: {description}")
    confirm = input("Submit report? (y/n): ").lower()
    
    if confirm == "y":
        reference = generate_reference()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Save to CSV
        with open(CSV_FILE, mode='a', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=HEADERS)
            writer.writerow({
                "reference": reference,
                "phone_number": phone_number,
                "category": category,
                "location": location,
                "severity": severity,
                "description": description,
                "timestamp": timestamp
            })
        
        print(f"\nReport submitted successfully! Reference: {reference}")
    else:
        print("Report cancelled.")

def view_reports(phone_number):
    try:
        with open(CSV_FILE, mode='r') as file:
            reader = csv.DictReader(file)
            user_reports = [row for row in reader if row['phone_number'] == phone_number]
            
            if not user_reports:
                print("No previous reports found.")
                return
                
            print(f"\nFound {len(user_reports)} report(s):")
            for i, report in enumerate(user_reports, 1):
                print(f"\nReport {i}:")
                print(f"Reference: {report['reference']}")
                print(f"Category: {report['category']}")
                print(f"Date: {report['timestamp']}")
                print(f"Severity: {report['severity']}")
                
            view_details = input("\nView full details of a report? (y/n): ").lower()
            if view_details == "y":
                report_num = int(input("Enter report number: ")) - 1
                if 0 <= report_num < len(user_reports):
                    report = user_reports[report_num]
                    print("\n=== Full Report Details ===")
                    for key, value in report.items():
                        print(f"{key.replace('_', ' ').title()}: {value}")
                else:
                    print("Invalid report number.")
    except FileNotFoundError:
        print("No reports database found.")

if __name__ == "__main__":
    init_csv()
    run_ussd_flow()