orderamt = float(input("Enter the order amount: "))
deliverydist = float(input("Enter the delivery distance (in kms): "))
cust = input("Enter the customer type: ")
custrate = int(input("Enter the customer rating (1-10): "))
restrate = int(input("Enter the restaurant rating (1-10): "))
prep = int(input("Enter the preparation time (in minutes): "))
pay = input("Enter the payment method: ")
weather = input("Enter the weather condition: ")
demand = input("Enter the demand level: ")
peak = input("Enter the peak-hour status: ")
cancel = int(input("Enter the previous cancellations: "))

dcharge = 0
disc = 0
priority = "Low"
risk = "Low"
rest = "Healthy"
decision = "Accepted"
final_amt = 0

if deliverydist <= 3:
    dcharge = 20
elif deliverydist <= 8:
    dcharge = 35
elif deliverydist <= 15:
    dcharge = 55
else:
    dcharge = 70

if cust == "premium" or cust == "vip":
    disc = disc + 50

if pay == "upi" or pay == "wallet":
    disc = disc + 30

if weather == "clear" and peak == "no":
    disc = disc + 20

if demand == "low" and peak == "no":
    disc = disc + 10

if orderamt > 500:
    disc = disc + 25

if pay == "card" and (cust == "premium" or cust == "vip"):
    disc = disc + 15

if disc > 200:
    disc = 200

if (custrate >= 8 and restrate >= 8) or (cust == "premium" and custrate >= 7):
    priority = "High"
elif (custrate >= 5 and restrate >= 5) or (demand == "medium" and peak == "no"):
    priority = "Medium"
else:
    priority = "Low"

if cancel >= 3 or (weather == "stormy" and peak == "yes") or (pay == "cash on delivery" and orderamt > 700):
    risk = "High"
elif cancel >= 1 or demand == "high" or (weather == "rainy" and peak == "yes"):
    risk = "Medium"
else:
    risk = "Low"

if restrate < 3 or prep > 45 or cancel >= 3:
    rest = "Needs Attention"
elif restrate >= 4 and prep <= 25 and cancel <= 1:
    rest = "Excellent"
else:
    rest = "Healthy"

if rest == "Needs Attention" and (demand == "high" or weather == "stormy"):
    rest = "Critical"
    
if rest == "Critical":
    decision = "Rejected"
elif risk == "High":
    decision = "Rejected"
elif rest == "Needs Attention" and demand == "high":
    decision = "Manual Review"
elif risk == "Medium" and (weather == "rainy" or peak == "yes"):
    decision = "Manual Review"
elif prep > 35 and demand == "high":
    decision = "Manual Review"
elif custrate <= 3 and restrate <= 3:
    decision = "Manual Review"
else:
    decision = "Accepted"

final_amt = orderamt + dcharge - disc
if final_amt < 0:
    final_amt = 0

print("Decision:", decision)
print("Delivery Charges: Rs", dcharge)
print("Discount: Rs", disc)
print("Priority Status:", priority)
print("Cancellation Risk:", risk)
print("Restaurant Status:", rest)
print("Final Payable Amount: Rs", final_amt)