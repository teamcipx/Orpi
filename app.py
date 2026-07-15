import os
import datetime
import random
import urllib.request
import urllib.parse
import json
import base64
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from supabase import create_client, Client
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "opti_work_secured_stable_permanent_key_998124")
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(days=30)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "YOUR_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "YOUR_SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def send_telegram_notification(text):
    token = "8922254680:AAEwgygDXJl0xjB9TPX-Rl0XeVAfVobQdXI"
    chat_id = "@ortipay"
    
    if token == "YOUR_BOT_TOKEN" or chat_id == "@your_channel_username":
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "Main Channel 📢", "url": "https://t.me/ortiwokr"},
                {"text": "Support Help 🤖", "url": "https://t.me/Optiworkhelp"}
            ]
        ]
    }
    
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": json.dumps(reply_markup)
    }).encode("utf-8")
    
    try:
        req = urllib.request.Request(url, data=data)
        urllib.request.urlopen(req)
    except Exception as e:
        print("Telegram API Error:", e)


def generate_fake_phone():
    prefixes = ['017', '019', '018', '015', '016', '013', '014']
    prefix = random.choice(prefixes)
    suffix = random.randint(100, 999)
    return f"{prefix}*****{suffix}"


def round_to_nearest_5(num):
    return round(num / 5) * 5


def generate_deposit_amount():
    roll = random.random()
    if roll < 0.75:
        amount = random.randint(100, 499)
    else:
        amount = random.randint(500, 1000)
    return float(round_to_nearest_5(amount))


def generate_withdraw_amount():
    roll = random.random()
    if roll < 0.10:
        amount = random.randint(300, 400)
    elif roll < 0.85:
        amount = random.randint(405, 999)
    else:
        amount = random.randint(1000, 2000)
    return float(round_to_nearest_5(amount))


@app.route('/api/cron/simulate-traffic', methods=['GET'])
def simulate_traffic_cron():
    cron_key = request.args.get('key')
    if cron_key != os.environ.get("CRON_SECRET_KEY", "secure_cron_key_123"):
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
    now = datetime.datetime.now(datetime.timezone.utc)
    
    due_success_tx = supabase.table("simulated_transactions") \
        .select("*") \
        .eq("status", "Pending") \
        .lte("scheduled_success_at", now.isoformat()) \
        .execute().data
        
    if not due_success_tx:
        for _ in range(random.randint(2, 3)):
            fake_uid = random.randint(1000, 6891)
            fake_phone = generate_fake_phone()
            method = random.choice(['bKash', 'Nagad'])
            tx_type = random.choice(['Deposit', 'Withdraw'])
            amount = generate_withdraw_amount() if tx_type == 'Withdraw' else generate_deposit_amount()
            
            supabase.table("simulated_transactions").insert({
                "uid": fake_uid,
                "phone_number": fake_phone,
                "amount": amount,
                "method": method,
                "type": tx_type,
                "status": "Success",
                "scheduled_success_at": now.isoformat()
            }).execute()
            
            success_msg = f"""<b>✅ {tx_type.upper()} SUCCESSFUL</b>
────────────────────
<b>User UID:</b> <code>#{fake_uid}</code>
<b>Amount:</b> ৳ {amount}
<b>Gateway:</b> {method}
<b>Number:</b> {fake_phone}
<b>Status:</b> 🟢 Completed (Success)
────────────────────
<i>Payout processed via Automated Node!</i>"""
            send_telegram_notification(success_msg)
    else:
        for tx in due_success_tx:
            if tx['type'] == 'Withdraw' and random.random() < 0.02:
                supabase.table("simulated_transactions").update({"status": "Rejected"}).eq("id", tx['id']).execute()
                
                reject_msg = f"""<b>❌ WITHDRAWAL REJECTED</b>
────────────────────
<b>User UID:</b> <code>#{tx['uid']}</code>
<b>Amount:</b> ৳ {tx['amount']}
<b>Gateway:</b> {tx['method']}
<b>Number:</b> {tx['phone_number']}
<b>Status:</b> 🔴 Rejected / Verification Failed
────────────────────
<i>Transaction declined by Automated Security System.</i>"""
                send_telegram_notification(reject_msg)
            else:
                supabase.table("simulated_transactions").update({"status": "Success"}).eq("id", tx['id']).execute()
                
                success_msg = f"""<b>✅ {tx['type'].upper()} SUCCESSFUL</b>
────────────────────
<b>User UID:</b> <code>#{tx['uid']}</code>
<b>Amount:</b> ৳ {tx['amount']}
<b>Gateway:</b> {tx['method']}
<b>Number:</b> {tx['phone_number']}
<b>Status:</b> 🟢 Completed (Success)
────────────────────
<i>Payout processed via Automated Node!</i>"""
                send_telegram_notification(success_msg)

    num_of_pending = random.randint(3, 4)
    for _ in range(num_of_pending):
        fake_uid = random.randint(1000, 6891)
        fake_phone = generate_fake_phone()
        method = random.choice(['bKash', 'Nagad'])
        
        if random.random() < 0.60:
            tx_type = 'Withdraw'
            amount = generate_withdraw_amount()
        else:
            tx_type = 'Deposit'
            amount = generate_deposit_amount()
            
        random_delay_minutes = random.randint(180, 240)
        scheduled_success = now + datetime.timedelta(minutes=random_delay_minutes)
        
        supabase.table("simulated_transactions").insert({
            "uid": fake_uid,
            "phone_number": fake_phone,
            "amount": amount,
            "method": method,
            "type": tx_type,
            "status": "Pending",
            "scheduled_success_at": scheduled_success.isoformat()
        }).execute()
        
        pending_msg = f"""<b>🚨 NEW {tx_type.upper()} REQUEST</b>
────────────────────
<b>User UID:</b> <code>#{fake_uid}</code>
<b>Amount:</b> ৳ {amount}
<b>Gateway:</b> {method}
<b>Number:</b> {fake_phone}
<b>Status:</b> 🟡 Pending (Processing)
────────────────────
<i>Request queued on Mining Server...</i>"""
        send_telegram_notification(pending_msg)
        
    return jsonify({"status": "completed", "instant_payouts_and_pendings_created": True}), 200


def mask_email(email):
    try:
        parts = email.split('@')
        name, domain = parts[0], parts[1]
        if len(name) > 3:
            return f"{name[:2]}***{name[-1]}@{domain}"
        return f"{name[0]}***@{domain}"
    except Exception:
        return "u***@email.com"

app.jinja_env.filters['mask_email'] = mask_email


def check_admin_auth():
    user_id = session.get('user_id')
    if not user_id:
        return None
    user = supabase.table("users").select("is_admin, is_banned").eq("id", user_id).execute().data
    if user and user[0]['is_admin'] and not user[0]['is_banned']:
        return user_id
    return None


# (অন্যান্য কোড অপরিবর্তিত থাকবে, app.py ফাইলের একদম ওপরের দিকে import math যুক্ত করে নিন এবং admin_dashboard রাউটটি নিচের কোড দ্বারা পরিবর্তন করুন)
import math

@app.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    if not check_admin_auth():
        return "Unauthorized Access", 403
        
    now = datetime.datetime.now(datetime.timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    
    all_users = supabase.table("users").select("id", count="exact").execute()
    total_users = all_users.count if all_users.count is not None else 0
    
    today_users_query = supabase.table("users").select("id", count="exact").gte("created_at", today_start).execute()
    today_users = today_users_query.count if today_users_query.count is not None else 0
    
    total_dep_query = supabase.table("deposits").select("amount").eq("status", "Approved").execute().data
    total_deposits = sum(float(d['amount']) for d in total_dep_query)
    
    today_dep_query = supabase.table("deposits").select("amount").eq("status", "Approved").gte("created_at", today_start).execute().data
    today_deposits = sum(float(d['amount']) for d in today_dep_query)
    
    pending_dep_res = supabase.table("deposits").select("id", count="exact").eq("status", "Pending").execute()
    pending_deposits_count = pending_dep_res.count if pending_dep_res.count is not None else 0
    
    pending_with_res = supabase.table("withdrawals").select("id", count="exact").eq("status", "Pending").execute()
    pending_withdrawals_count = pending_with_res.count if pending_with_res.count is not None else 0
    
    pending_tasks_res = supabase.table("task_submissions").select("id", count="exact").eq("status", "Pending").execute()
    pending_tasks_count = pending_tasks_res.count if pending_tasks_res.count is not None else 0
    
    # --- পেজিনেশন ক্যালকুলেশন (২০ জন করে প্রতি পেজে) ---
    page = int(request.args.get('page', 1))
    limit = 20
    start = (page - 1) * limit
    end = start + limit - 1
    
    search_query = request.args.get('search', '').strip()
    users_list = []
    
    if search_query:
        # সার্চ করা হলে ফিল্টার করা ইউজার তালিকা এবং পেজিনেশন রেঞ্জ লিমিট
        query_builder = supabase.table("users").select("id, uid, username, email, balance, is_banned, device_name")
        
        if search_query.isdigit():
            u_res = query_builder.eq("uid", int(search_query)).range(start, end).execute()
        else:
            u_res = query_builder.or_(f"email.ilike.%{search_query}%,username.ilike.%{search_query}%").range(start, end).execute()
            
        users_list = u_res.data or []
        has_next = len(users_list) == limit
        has_prev = page > 1
    else:
        # ডিফল্টভাবে সমস্ত ইউজারদের মেম্বার তালিকা পেজিনেশন রেঞ্জ লিমিট সহ
        u_res = supabase.table("users").select("id, uid, username, email, balance, is_banned, device_name") \
            .order("created_at", desc=True).range(start, end).execute()
            
        users_list = u_res.data or []
        total_pages = math.ceil(total_users / limit)
        has_next = page < total_pages
        has_prev = page > 1

    return render_template('admin.html', 
                           total_users=total_users, 
                           today_users=today_users, 
                           total_deposits=total_deposits, 
                           today_deposits=today_deposits, 
                           pending_deposits_count=pending_deposits_count,
                           pending_withdrawals_count=pending_withdrawals_count,
                           pending_tasks_count=pending_tasks_count,
                           users_list=users_list,
                           search_query=search_query,
                           page=page,
                           has_next=has_next,
                           has_prev=has_prev)
    
# (অন্যান্য এডমিন রাউটের সাথে নিচের সংশোধিত রাউটটি যুক্ত করুন)

# app.py ফাইলের একদম নিচে এই এরর হ্যান্ডলার রাউট দুটি যুক্ত করুন:

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500
    
@app.route('/admin/payout')
def admin_payout_generator():
    if not check_admin_auth():
        return "Unauthorized Access", 403
        
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    five_hours_ago = (now_utc - datetime.timedelta(hours=5)).isoformat()
    
    # ১. বিগত ৫ ঘণ্টার রিয়াল উইথড্রয়াল ডাটা রিট্রিভ করা (Pending বাদে)
    real_w = supabase.table("withdrawals") \
        .select("amount, status, user_id") \
        .neq("status", "Pending") \
        .gte("created_at", five_hours_ago).execute().data or []
        
    # ২. বিগত ৫ ঘণ্টার চ্যানেলের ফেক উইথড্রয়াল ডাটা রিট্রিভ করা (Pending বাদে)
    fake_w = supabase.table("simulated_transactions") \
        .select("amount, status, uid") \
        .eq("type", "Withdraw") \
        .neq("status", "Pending") \
        .gte("created_at", five_hours_ago).execute().data or []
        
    # ৩. পেন্ডিং সম্পূর্ণ বাদ দিয়ে সফল ও বাতিল পেমেন্টের পৃথক হিসাব
    success_real = [w for w in real_w if w['status'] == 'Approved']
    success_fake = [fw for fw in fake_w if fw['status'] == 'Success']
    
    rejected_real = [w for w in real_w if w['status'] == 'Rejected']
    rejected_fake = [fw for fw in fake_w if fw['status'] == 'Rejected']
    
    # ৪. টোটাল সফল বিতরণ ও ট্রানজেকশন কাউন্ট
    total_success_amount = sum(float(w['amount']) for w in success_real) + sum(float(fw['amount']) for fw in success_fake)
    total_success_count = len(success_real) + len(success_fake)
    
    # ৫. টোটাল বাতিলকৃত বিতরণ ও ট্রানজেকশন কাউন্ট
    total_rejected_amount = sum(float(w['amount']) for w in rejected_real) + sum(float(fw['amount']) for fw in rejected_fake)
    total_rejected_count = len(rejected_real) + len(rejected_fake)
    
    # বাংলাদেশ সময় জেনারেশন (UTC+6)
    now_bd = now_utc + datetime.timedelta(hours=6)
    generation_time = now_bd.strftime("%d %b %Y, %I:%M %p")
    
    return render_template('admin_payout.html',
                           total_success_amount=total_success_amount,
                           total_success_count=total_success_count,
                           total_rejected_amount=total_rejected_amount,
                           total_rejected_count=total_rejected_count,
                           generation_time=generation_time)

# (অন্যান্য রাউটের সাথে নিচের নতুন রাউটটি যুক্ত করুন)

# (অন্যান্য কোডের সাথে জিমেইল মডারেটর এবং ইউজার রাউটগুলো নিচে যুক্ত করুন)

# ১. ইউজার জিমেইল সাবমিশন পেজ রাউট (/gmails)
@app.route('/gmails', methods=['GET', 'POST'])
def gmail_tasks():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    user = supabase.table("users").select("*").eq("id", user_id).execute().data[0]
    
    # ডাটাবেজ সেটিংস থেকে লাইভ জিমেইল রেট রিট্রিভ করা হচ্ছে
    price_res = supabase.table("settings").select("value").eq("key", "gmail_price").execute().data
    gmail_price = float(price_res[0]['value']) if price_res else 15.00
    
    if request.method == 'POST':
        email_input = request.form.get('gmail_address')
        pass_input = request.form.get('gmail_password')
        
        if not email_input or not pass_input:
            flash("দয়া করে জিমেইল এবং পাসওয়ার্ড দুটিই ইনপুট দিন।", "danger")
            return redirect(url_for('gmail_tasks'))
            
        try:
            supabase.table("gmail_submissions").insert({
                "user_id": user_id,
                "email": email_input.strip(),
                "password": pass_input.strip(),
                "price": gmail_price, # সাবমিট করার সময়ের নির্ধারিত মূল্য ডাটাবেজে লক থাকবে
                "status": "Pending"
            }).execute()
            flash("জিমেইল অ্যাকাউন্টটি সফলভাবে জমা দেওয়া হয়েছে। এডমিন ভেরিফাই করবে।", "success")
            return redirect(url_for('gmail_tasks'))
        except Exception:
            flash("ত্রুটি ঘটেছে। আবার চেষ্টা করুন।", "danger")
            
    # এই ইউজারের পূর্ববর্তী জিমেইল সাবমিশন হিস্ট্রি রিট্রিভ করা
    submissions = supabase.table("gmail_submissions") \
        .select("*") \
        .eq("user_id", user_id) \
        .order("created_at", desc=True).execute().data or []
        
    return render_template('gmails.html', user=user, gmail_price=gmail_price, submissions=submissions)


# ২. এডমিন জিমেইল রিভিউ ও রেট পরিবর্তনের পেজ রাউট (/admin/gmails)
@app.route('/admin/gmails', methods=['GET', 'POST'])
def admin_gmails():
    if not check_admin_auth():
        return "Unauthorized Access", 403
        
    # রেট আপডেট ফরম হ্যান্ডলিং
    if request.method == 'POST':
        new_price = request.form.get('new_price')
        if new_price:
            supabase.table("settings").upsert({"key": "gmail_price", "value": str(new_price)}).execute()
            flash("জিমেইলের অফিশিয়াল ক্রয়মূল্য সফলভাবে আপডেট করা হয়েছে।", "success")
            return redirect(url_for('admin_gmails'))
            
    # লাইভ জিমেইল প্রাইস এবং পেন্ডিং জিমেইলসমূহ রিট্রিভ করা
    price_res = supabase.table("settings").select("value").eq("key", "gmail_price").execute().data
    gmail_price = float(price_res[0]['value']) if price_res else 15.00
    
    pending_list = supabase.table("gmail_submissions") \
        .select("*, users:user_id(username, email, uid)") \
        .eq("status", "Pending") \
        .order("created_at", desc=True).execute().data or []
        
    return render_template('admin_gmails.html', pending_gmails=pending_list, gmail_price=gmail_price)


# ৩. এডমিন জিমেইল এপ্রুভ/রিজেক্ট অ্যাকশন রাউট (/admin/gmail-action)
@app.route('/admin/gmail-action', methods=['POST'])
def admin_gmail_action():
    if not check_admin_auth():
        return "Unauthorized Action", 403
        
    submission_id = request.form.get('submission_id')
    action = request.form.get('action') # 'approve' or 'reject'
    
    sub_query = supabase.table("gmail_submissions").select("*").eq("id", submission_id).execute().data
    if not sub_query:
        flash("রেকর্ড খুঁজে পাওয়া যায়নি।", "danger")
        return redirect(url_for('admin_gmails'))
        
    sub = sub_query[0]
    target_user_id = sub['user_id']
    price = float(sub['price'])
    sub_email = sub['email']
    
    if action == 'approve':
        # স্ট্যাটাস Approved করা
        supabase.table("gmail_submissions").update({"status": "Approved"}).eq("id", submission_id).execute()
        # ইউজারের মূল ব্যালেন্সে টাকা যোগ করা
        supabase.rpc("increment_balance", {"user_id": target_user_id, "amount": price}).execute()
        
        # লেনদেন হিস্ট্রি বা লগ সেভ করা
        supabase.table("transactions").insert({
            "user_id": target_user_id,
            "title": f"Gmail Account Sold: {sub_email}",
            "amount": price
        }).execute()
        
        flash("জিমেইল অ্যাকাউন্টটি সফলভাবে এপ্রুভ এবং রিওয়ার্ড যোগ করা হয়েছে।", "success")
    elif action == 'reject':
        supabase.table("gmail_submissions").update({"status": "Rejected"}).eq("id", submission_id).execute()
        flash("জিমেইল অ্যাকাউন্টটি রিজেক্ট করা হয়েছে।", "success")
        
    return redirect(url_for('admin_gmails'))

# (অন্যান্য রাউটের সাথে নিচের নতুন রাউটটি যুক্ত করুন)

@app.route('/tutorial')
def tutorial_page():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    user = supabase.table("users").select("*").eq("id", user_id).execute().data[0]
    return render_template('tutorial.html', user=user)
    
@app.route('/fasset')
def fasset_landing():
    user_id = session.get('user_id')
    user = None
    if user_id:
        try:
            user_data = supabase.table("users").select("username", "uid", "avatar_url").eq("id", user_id).execute().data
            if user_data:
                user = user_data[0]
        except Exception:
            pass
    return render_template('fasset.html', user=user)

# (অন্যান্য এডমিন রাউটের সাথে নিচের নতুন রাউটটি যুক্ত করুন)

@app.route('/admin/task-bulk-action', methods=['POST'])
def admin_task_bulk_action():
    if not check_admin_auth():
        return "Unauthorized Action", 403
        
    # ১. প্রথম ২০টি পেন্ডিং সাবমিশন রিট্রিভ করা
    pending_subs = supabase.table("task_submissions") \
        .select("id, user_id, tasks(title, reward)") \
        .eq("status", "Pending") \
        .limit(20).execute().data or []
        
    if not pending_subs:
        flash("বর্তমানে কোনো পেন্ডিং টাস্ক সাবমিশন নেই।", "danger")
        return redirect(url_for('admin_add_task'))
        
    total_count = len(pending_subs)
    
    # ২. র্যান্ডম রিজেকশন সংখ্যা নির্ধারণ (২/৩টি রিজেক্ট করার সুনির্দিষ্ট লজিক)
    if total_count >= 10:
        reject_count = random.randint(2, 3) # ১০ বা তার বেশি হলে ২/৩টি রিজেক্ট হবে
    elif total_count >= 3:
        reject_count = 1                   # ৩টির বেশি হলে ১টি রিজেক্ট হবে
    else:
        reject_count = 0                   # ৩টির নিচে হলে সব এপ্রুভ হবে
        
    # র্যান্ডমলি কোন কোন ইনডেক্স রিজেক্ট হবে তা সিলেক্ট করা হচ্ছে
    reject_indices = set(random.sample(range(total_count), reject_count))
    
    approved_count = 0
    rejected_count = 0
    
    # ৩. বাল্ক লুপিং প্রসেস
    for index, sub in enumerate(pending_subs):
        submission_id = sub['id']
        target_user_id = sub['user_id']
        reward = float(sub['tasks']['reward']) if sub.get('tasks') else 0.00
        task_title = sub['tasks']['title'] if sub.get('tasks') else "Task"
        
        if index in reject_indices:
            # রিজেক্ট করা হচ্ছে
            supabase.table("task_submissions").update({"status": "Rejected"}).eq("id", submission_id).execute()
            rejected_count += 1
        else:
            # এপ্রুভ করা হচ্ছে
            supabase.table("task_submissions").update({"status": "Approved"}).eq("id", submission_id).execute()
            # ব্যালেন্স অ্যাড করা হচ্ছে
            supabase.rpc("increment_balance", {"user_id": target_user_id, "amount": reward}).execute()
            
            # লেনদেন হিস্ট্রি লগ সেভ
            supabase.table("transactions").insert({
                "user_id": target_user_id,
                "title": f"Task Approved: {task_title}",
                "amount": reward
            }).execute()
            approved_count += 1
            
    flash(f"বাল্ক অটো-ভেরিফিকেশন সম্পন্ন! {approved_count}টি টাস্ক Approved এবং {rejected_count}টি টাস্ক Rejected করা হয়েছে।", "success")
    return redirect(url_for('admin_add_task'))
    
# app.py ফাইলের /reviews রাউটটি এটি দিয়ে প্রতিস্থাপন করে নিন:

# (অন্যান্য কোডের সাথে নিচের নতুন আপডেট এবং এডমিন পোস্ট রাউট দুটি যুক্ত করুন)

# ১. মেম্বার প্যানেল আপডেট পেজ রাউট (/updates)
@app.route('/updates')
def updates_page():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    user = supabase.table("users").select("*").eq("id", user_id).execute().data[0]
    
    # সর্বশেষ পোস্টটি সবার আগে পেতে ডিক্রিজিং বা ডেসেন্ডিং অর্ডারে সাজানো
    all_updates = supabase.table("updates").select("*").order("created_at", desc=True).execute().data or []
    
    return render_template('updates.html', user=user, updates=all_updates)


# ২. এডমিন কতৃক নতুন আপডেট নোটিশ যুক্ত করার রাউট
@app.route('/admin/add-update', methods=['POST'])
def admin_add_update():
    if not check_admin_auth():
        return "Unauthorized Action", 403
        
    post_path = request.form.get('post_path').strip()
    
    # এডমিন যদি কেবল পোস্ট আইডি (যেমন: 49) টাইপ করে, তবে তা স্বয়ংক্রিয়ভাবে অরিজিনাল পাথে কনভার্ট হবে
    if post_path.isdigit():
        post_path = f"ortiwokr/{post_path}"
        
    try:
        supabase.table("updates").insert({"post_path": post_path}).execute()
        flash("নতুন চ্যানেল আপডেট সফলভাবে ড্যাশবোর্ডে পোস্ট করা হয়েছে।", "success")
    except Exception:
        flash("এই আপডেটটি ইতিমধ্যে পোস্ট করা রয়েছে।", "danger")
        
    return redirect(url_for('admin_add_task'))
    
@app.route('/reviews', methods=['GET', 'POST'])
def reviews_page():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    user = supabase.table("users").select("username, is_admin").eq("id", user_id).execute().data[0]
    is_admin = user.get('is_admin', False)
    
    if request.method == 'POST':
        comment = request.form.get('comment')
        rating = int(request.form.get('rating', 5))
        image_url = request.form.get('image_url')
        
        insert_data = {
            "user_id": user_id,
            "reviewer_name": user['username'],
            "rating": rating,
            "comment": comment,
            "is_admin_fake": False
        }
        
        if image_url and image_url.strip() != "":
            insert_data["image_url"] = image_url.strip()
            
        try:
            supabase.table("reviews").insert(insert_data).execute()
            flash("আপনার মূল্যবান মতামতটি সফলভাবে জমা হয়েছে।", "success")
        except Exception:
            flash("রিভিউ জমা দিতে ত্রুটি ঘটেছে। অনুগ্রহ করে আবার চেষ্টা করুন।", "danger")
            
        return redirect(url_for('reviews_page'))
        
    # --- ১০০% নিরাপদ পাইথন-লেভেল ফিল্টারিং ও রেন্ডারিং ---
    try:
        # প্রথমে ডাটাবেজ থেকে কোনো ফিল্টার ছাড়া সম্পূর্ণ জেনেরিক তালিকা নিয়ে আসা হচ্ছে (যা কখনোই ক্র্যাশ করবে না)
        all_reviews = supabase.table("reviews").select("*").execute().data or []
        
        reviews_data = []
        for r in all_reviews:
            if is_admin:
                # এডমিন হলে সব দেখতে পাবেন
                reviews_data.append(r)
            else:
                # সাধারণ মেম্বার হলে:
                # ১. এডমিনের তৈরি ফেক রিভিউগুলো দেখতে পাবেন (is_admin_fake == True)
                # ২. অথবা নিজের তৈরি করা রিভিউটি দেখতে পাবেন (user_id ম্যাচ করলে)
                db_user_id = str(r.get('user_id')) if r.get('user_id') else None
                if r.get('is_admin_fake') == True or db_user_id == str(user_id):
                    reviews_data.append(r)
            
        # তারিখ অনুযায়ী সাজানো (Newest first)
        reviews_data.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    except Exception as e:
        print("Reviews Filter Error:", e)
        reviews_data = []
            
    return render_template('reviews.html', reviews=reviews_data, is_admin=is_admin)
    

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        phone = request.form.get('phone_number')
        age = request.form.get('age')
        district = request.form.get('district')
        proof_url = request.form.get('avatar_url')
        username = request.form.get('username')
        
        update_data = {}
        if username: update_data['username'] = username
        if phone: update_data['phone_number'] = phone
        if age: update_data['age'] = int(age) if age.isdigit() else None
        if district: update_data['district'] = district
        if proof_url: update_data['avatar_url'] = proof_url
        
        if update_data:
            supabase.table("users").update(update_data).eq("id", user_id).execute()
            flash("প্রোফাইল তথ্য সফলভাবে আপডেট করা হয়েছে।", "success")
            return redirect(url_for('profile'))
            
    user = supabase.table("users").select("*").eq("id", user_id).execute().data[0]
    ref_link = request.url_root + "register?ref=" + str(user['uid'])
    
    return render_template('profile.html', user=user, ref_link=ref_link)
    
@app.route('/about')
def about():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    user = supabase.table("users").select("*").eq("id", user_id).execute().data[0]
    return render_template('about.html', user=user)

@app.route('/referrals')
def referrals():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    user = supabase.table("users").select("uid").eq("id", user_id).execute().data[0]
    
    # ডাটাবেজ থেকে সরাসরি রেফারেল হিস্ট্রি ডেটা রিট্রিভ করা হচ্ছে
    referrals_data = supabase.table("referrals") \
        .select("status, created_at, users:referred_id(username, email)") \
        .eq("referrer_id", user_id).execute().data or []
        
    success_count = 0
    processing_count = 0
    failed_count = 0
    
    for r in referrals_data:
        status = r.get('status', 'Processing')
        if status == 'Success':
            success_count += 1
        elif status == 'Processing':
            processing_count += 1
        elif status == 'Failed':
            failed_count += 1
            
    # রেফার প্রতি ১৫ টাকা সফল কমিশন হিসাব
    total_earnings = success_count * 15.00
    ref_link = request.url_root + "register?ref=" + str(user['uid'])
    
    return render_template('referrals.html', 
                           referrals=referrals_data, 
                           ref_link=ref_link,
                           success_count=success_count,
                           processing_count=processing_count,
                           failed_count=failed_count,
                           total_earnings=total_earnings)
    
# (অন্যান্য এডমিন রাউটের সাথে নিচের নতুন রাউট দুটি যুক্ত করুন)

# ১. এডমিন উইথড্রয়াল লিস্ট রাউট
@app.route('/admin/withdrawals')
def admin_withdrawals():
    if not check_admin_auth():
        return "Unauthorized Access", 403
        
    # পেন্ডিং থাকা উইথড্রয়ালগুলো এবং ইউজারের ডেটা রিট্রিভ করা (Postgrest standard join)
    pending = supabase.table("withdrawals") \
        .select("*, users:user_id(username, email, uid)") \
        .eq("status", "Pending") \
        .order("created_at", desc=True).execute().data or []
        
    return render_template('admin_withdraw.html', pending_withdrawals=pending)


# ২. উইথড্র এপ্রুভ/রিজেক্ট অ্যাকশন এবং অটোমেটিক টেলিগ্রাম নোটিফিকেশন ট্রিগার
@app.route('/admin/withdraw-action', methods=['POST'])
def admin_withdraw_action():
    if not check_admin_auth():
        return "Unauthorized Action", 403
        
    withdraw_id = request.form.get('withdraw_id')
    action = request.form.get('action') # 'approve' অথবা 'reject'
    
    # উইথড্রয়াল তথ্য ও রেফার করা ইউজারের UID সংগ্রহ করা
    withdraw_query = supabase.table("withdrawals") \
        .select("*, users:user_id(uid)") \
        .eq("id", withdraw_id).execute().data
        
    if not withdraw_query:
        flash("উইথড্র রেকর্ড পাওয়া যায়নি।", "danger")
        return redirect(url_for('admin_withdrawals'))
        
    w = withdraw_query[0]
    user_id = w['user_id']
    amount = float(w['amount'])
    uid = w['users']['uid']
    method = w['payment_method']
    number = w['payment_number']
    is_agent = w.get('is_agent_withdrawal', False)
    
    if action == 'approve':
        # ১. ডাটাবেজে স্ট্যাটাস Approved করা
        supabase.table("withdrawals").update({"status": "Approved"}).eq("id", withdraw_id).execute()
        
        # ২. টেলিগ্রাম চ্যানেলে ইনলাইন বাটন সহ SUCCESS নোটিফিকেশন পাঠানো
        masked_number = number[:3] + "*****" + number[-3:]
        success_msg = f"""<b>✅ WITHDRAWAL SUCCESSFUL</b>
────────────────────
<b>User UID:</b> <code>#{uid}</code>
<b>Amount:</b> ৳ {amount}
<b>Gateway:</b> {method}
<b>Number:</b> {masked_number}
<b>Status:</b> 🟢 Completed (Success)
────────────────────
<i>Payout processed via Automated Node!</i>"""
        send_telegram_notification(success_msg)
        
        flash("উইথড্র রিকোয়েস্ট সফলভাবে এপ্রুভ এবং টেলিগ্রামে পোস্ট করা হয়েছে।", "success")
        
    elif action == 'reject':
        # ১. ডাটাবেজে স্ট্যাটাস Rejected করা
        supabase.table("withdrawals").update({"status": "Rejected"}).eq("id", withdraw_id).execute()
        
        # ২. টাকা রিফান্ড করা (এজেন্ট উইথড্র হলে এজেন্ট ব্যালেন্সে, সাধারণ উইথড্র হলে মূল ব্যালেন্সে)
        if is_agent:
            supabase.rpc("increment_agent_balance", {"user_id": user_id, "amount": amount}).execute()
        else:
            supabase.rpc("increment_balance", {"user_id": user_id, "amount": amount}).execute()
            
        flash("উইথড্র রিকোয়েস্ট রিজেক্ট করা হয়েছে এবং ব্যালেন্স সফলভাবে রিফান্ড হয়েছে।", "success")
        
    return redirect(url_for('admin_withdrawals'))
    

# (অন্যান্য কোডের সাথে নিচের ডাইনামিক আপলোডার এবং এডমিন কি-ম্যানেজার রাউটগুলো যুক্ত করুন)

# ১. সুরক্ষিত অটো-ফেইলওভার আপলোডার এপিআই (১০০% সাকসেস গ্যারান্টি)
@app.route('/api/upload', methods=['POST'])
def api_upload_image():
    if 'image' not in request.files:
        return jsonify({"status": "error", "message": "No image file provided."}), 400
        
    file = request.files['image']
    file_bytes = file.read()
    base64_image = base64.b64encode(file_bytes)
    
    # ফেইলওভার হ্যান্ডলিং লুপ
    while True:
        # ডাটাবেজ থেকে প্রথম সচল (Active) কি-টি কুয়েরি করা হচ্ছে
        keys_query = supabase.table("imgbb_keys") \
            .select("id, key_value") \
            .eq("status", "Active") \
            .order("created_at", desc=False) \
            .limit(1).execute().data
            
        if not keys_query:
            return jsonify({"status": "error", "message": "কোনো সক্রিয় ImgBB API Key পাওয়া যায়নি। দয়া করে এডমিনের সাথে যোগাযোগ করুন।"}), 500
            
        key_id = keys_query[0]['id']
        key_value = keys_query[0]['key_value']
        
        # আপলোড করার চেষ্টা
        try:
            payload = urllib.parse.urlencode({
                "image": base64_image
            }).encode("utf-8")
            
            url = f"https://api.imgbb.com/1/upload?key={key_value}"
            req = urllib.request.Request(url, data=payload)
            
            with urllib.request.urlopen(req) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                
            if res_data.get('success'):
                # সফল হলে সরাসরি ইমেজ লিংক ফ্রন্টএন্ডে রিটার্ন করবে
                return jsonify({"status": "success", "url": res_data['data']['url']}), 200
            else:
                raise Exception("Upload rejected")
                
        except Exception:
            # কনেকশন ফেইল বা কি ব্লকড হলে ডাটাবেজে স্ট্যাটাস Failed করে দেওয়া হচ্ছে
            supabase.table("imgbb_keys").update({"status": "Failed"}).eq("id", key_id).execute()
            # লুপটি পুনরায় চলবে এবং পরবর্তী সক্রিয় কি-টি দিয়ে আপলোড শুরু করবে


# ২. এডমিন এপিআই কি ম্যানেজার রাউট (/admin/keys)
@app.route('/admin/keys', methods=['GET', 'POST'])
def admin_keys():
    if not check_admin_auth():
        return "Unauthorized Access", 403
        
    if request.method == 'POST':
        new_key = request.form.get('key_value')
        if new_key:
            try:
                supabase.table("imgbb_keys").insert({"key_value": new_key.strip(), "status": "Active"}).execute()
                flash("নতুন ImgBB API Key সফলভাবে সচল তালিকায় যুক্ত করা হয়েছে।", "success")
            except Exception:
                flash("এই এপিআই কী-টি ইতিমধ্যে ডাটাবেজে রয়েছে।", "danger")
        return redirect(url_for('admin_keys'))
        
    # সমস্ত কি-সমূহের তালিকা
    all_keys = supabase.table("imgbb_keys").select("*").order("created_at", desc=True).execute().data or []
    return render_template('admin_keys.html', keys=all_keys)


# ৩. এডমিন এপিআই কি ডিলিট রাউট
@app.route('/admin/keys/delete', methods=['POST'])
def admin_delete_key():
    if not check_admin_auth():
        return "Unauthorized Action", 403
        
    key_id = request.form.get('key_id')
    supabase.table("imgbb_keys").delete().eq("id", key_id).execute()
    flash("এপিআই কী-টি ডাটাবেজ থেকে মুছে ফেলা হয়েছে।", "success")
    return redirect(url_for('admin_keys'))
    
@app.route('/agent')
def agent_portal():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    user = supabase.table("users").select("*").eq("id", user_id).execute().data[0]
    
    if not user.get('is_agent'):
        return "Access Denied (403)", 403
        
    referred_users = supabase.table("referrals") \
        .select("status, created_at, users:referred_id(id, uid, username, email, balance)") \
        .eq("referrer_id", user_id).execute().data
        
    referred_ids = [r['users']['id'] for r in referred_users if r.get('users')]
    
    deposits_list = []
    if referred_ids:
        deposits_list = supabase.table("deposits") \
            .select("amount, status, created_at, users(username, uid)") \
            .in_("user_id", referred_ids) \
            .eq("status", "Approved") \
            .order("created_at", desc=True).execute().data

    withdraw_history = supabase.table("withdrawals") \
        .select("*") \
        .eq("user_id", user_id) \
        .eq("is_agent_withdrawal", True) \
        .order("created_at", desc=True).execute().data

    return render_template('agent.html', 
                           user=user, 
                           referred_users=referred_users, 
                           deposits=deposits_list,
                           withdraw_history=withdraw_history)


@app.route('/agent/withdraw', methods=['POST'])
def agent_withdraw():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    user = supabase.table("users").select("is_agent, agent_balance").eq("id", user_id).execute().data[0]
    if not user.get('is_agent'):
        return "Unauthorized Action", 403
        
    agent_balance = float(user['agent_balance'])
    amount = float(request.form.get('amount'))
    method = request.form.get('method')
    number = request.form.get('number')
    
    if amount < 50.00:
        flash("এজেন্ট উইথড্রয়াল ন্যূনতম ৫০ টাকা হতে হবে।", "danger")
    elif amount > agent_balance:
        flash("আপনার এজেন্ট ব্যালেন্স অপর্যাপ্ত।", "danger")
    else:
        supabase.rpc("increment_agent_balance", {"user_id": user_id, "amount": -amount}).execute()
        
        supabase.table("withdrawals").insert({
            "user_id": user_id,
            "amount": amount,
            "payment_method": method,
            "payment_number": number,
            "status": "Pending",
            "is_agent_withdrawal": True
        }).execute()
        
        flash("এজেন্ট উইথড্রয়াল অনুরোধ সফলভাবে জমা হয়েছে।", "success")
        
    return redirect(url_for('agent_portal'))



@app.route('/admin/deposits')
def admin_deposits():
    if not check_admin_auth():
        return "Unauthorized Access", 403
        
    # পেন্ডিং থাকা ডিপোজিটসমূহ এবং ইউজারের ইউনিক তথ্য সংগ্রহ (Postgrest standard join)
    pending = supabase.table("deposits") \
        .select("*, users:user_id(username, email, uid)") \
        .eq("status", "Pending") \
        .order("created_at", desc=True).execute().data or []
        
    return render_template('admin_deposit.html', pending_deposits=pending)

@app.route('/admin/deposit-action', methods=['POST'])
def admin_deposit_action():
    if not check_admin_auth():
        return "Unauthorized Action", 403
        
    deposit_id = request.form.get('deposit_id')
    action = request.form.get('action') # 'approve' অথবা 'reject'
    
    dep_query = supabase.table("deposits").select("*").eq("id", deposit_id).execute().data
    if not dep_query:
        flash("ডিপোজিট রেকর্ড পাওয়া যায়নি।", "danger")
        return redirect(url_for('admin_deposits'))
        
    dep = dep_query[0]
    target_user_id = dep['user_id']
    amount = float(dep['amount'])
    
    if action == 'approve':
        # ১. ডাটাবেজে ডিপোজিট স্ট্যাটাস 'Approved' করা
        supabase.table("deposits").update({"status": "Approved"}).eq("id", deposit_id).execute()
        
        # ২. ইউজারের মূল ব্যালেন্সে টাকা যোগ করা
        supabase.rpc("increment_balance", {"user_id": target_user_id, "amount": amount}).execute()
        
        # ৩. আপলাইন এজেন্ট চেক করে ৫০% কমিশন প্রদান করা
        ref_query = supabase.table("referrals").select("referrer_id").eq("referred_id", target_user_id).execute().data
        if ref_query:
            referrer_id = ref_query[0]['referrer_id']
            referrer_user = supabase.table("users").select("is_agent").eq("id", referrer_id).execute().data
            if referrer_user and referrer_user[0]['is_agent']:
                commission = amount * 0.50
                supabase.rpc("increment_agent_balance", {"user_id": referrer_id, "amount": commission}).execute()
                
        flash("ডিপোজিট এপ্রুভ এবং ব্যালেন্স সফলভাবে যোগ করা হয়েছে।", "success")
    elif action == 'reject':
        # ডিপোজিট বাতিল করা
        supabase.table("deposits").update({"status": "Rejected"}).eq("id", deposit_id).execute()
        flash("ডিপোজিট রিকোয়েস্ট রিজেক্ট করা হয়েছে।", "success")
        
    # অ্যাকশন শেষ হওয়ার পর পুনরায় ডিপোজিট লিস্ট পেজে রিডাইরেক্ট করা
    return redirect(url_for('admin_deposits'))
    

@app.route('/admin/reviews/create', methods=['POST'])
def admin_create_fake_review():
    user_id = session.get('user_id')
    if not user_id or not check_admin_auth():
        return "Unauthorized Action", 403
        
    fake_name = request.form.get('fake_name')
    rating = int(request.form.get('rating', 5))
    comment = request.form.get('comment')
    image_url = request.form.get('image_url')
    custom_date = request.form.get('custom_date')
    
    review_data = {
        "reviewer_name": fake_name,
        "rating": rating,
        "comment": comment,
        "is_admin_fake": True
    }
    
    if image_url and image_url.strip() != "":
        review_data["image_url"] = image_url.strip()
        
    if custom_date:
        try:
            parsed_date = datetime.datetime.strptime(custom_date, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
            review_data["created_at"] = parsed_date.isoformat()
        except Exception as date_err:
            print("Date Parse Error:", date_err)
            
    try:
        supabase.table("reviews").insert(review_data).execute()
        flash("ফেক রিভিউটি সফলভাবে লাইভ করা হয়েছে।", "success")
    except Exception as e:
        error_msg = str(e)
        flash(f"ডাটাবেজ ত্রুটি: {error_msg}", "danger")
        print("Database Insert Error:", error_msg)
        
    return redirect(url_for('reviews_page'))


@app.route('/admin/reviews/delete', methods=['POST'])
def admin_delete_review():
    user_id = session.get('user_id')
    if not user_id or not check_admin_auth():
        return "Unauthorized Action", 403
        
    review_id = request.form.get('review_id')
    try:
        supabase.table("reviews").delete().eq("id", review_id).execute()
        flash("রিভিউটি সফলভাবে ডিলিট করা হয়েছে।", "success")
    except Exception:
        flash("রিভিউটি ডিলিট করা যায়নি।", "danger")
        
    return redirect(url_for('reviews_page'))
    
# (অন্যান্য কোড অপরিবর্তিত থাকবে, টাস্ক সম্পর্কিত রাউটগুলো নিচের কোড দ্বারা প্রতিস্থাপন করুন)

# ১. টাস্ক তালিকা রাউট (/tasks)
@app.route('/tasks')
def tasks():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    user = supabase.table("users").select("*").eq("id", user_id).execute().data[0]
    
    # ইউজার ইতিমধ্যে ক্লেইম করা ওয়ান-টাইম টাস্কগুলোর তালিকা
    completed_one_times = supabase.table("user_one_time_tasks") \
        .select("task_name").eq("user_id", user_id).execute().data
    claimed_one_times = [t['task_name'] for t in completed_one_times]
    
    # সফল রেফারেল সংখ্যা যাচাই
    success_refs_query = supabase.table("referrals").select("id").eq("referrer_id", user_id).eq("status", "Success").execute().data
    success_ref_count = len(success_refs_query)
    
    # প্রোফাইল সম্পূর্ণ করা হয়েছে কিনা যাচাই করা
    is_profile_complete = bool(user.get('phone_number') and user.get('age') and user.get('district'))
    
    # ইউজারের সাবমিট করা পূর্ববর্তী নরমাল টাস্কের ডাটা
    submissions = supabase.table("task_submissions").select("task_id, status").eq("user_id", user_id).execute().data
    submission_map = {s['task_id']: s['status'] for s in submissions}
    
    # এডমিনের তৈরি সমস্ত নরমাল টাস্কসমূহ
    all_normal_tasks = supabase.table("tasks").select("*").order("created_at", desc=True).execute().data
    
    # ফিল্টারিং লজিক: কেবল সেই কাজগুলোই দেখাবে যা ইউজার সাবমিট করেনি অথবা পূর্বে 'Rejected' হয়েছে
    active_normal_tasks = []
    for task in all_normal_tasks:
        status = submission_map.get(task['id'])
        if status is None or status == 'Rejected':
            active_normal_tasks.append(task)

    return render_template('tasks.html', 
                           claimed_one_times=claimed_one_times,
                           success_ref_count=success_ref_count,
                           is_profile_complete=is_profile_complete,
                           all_normal_tasks=active_normal_tasks,
                           submission_map=submission_map)


# ২. ডেডিকেটেড টাস্ক ডিটেইলস ও স্টেপ-বাই-স্টেপ সাবমিশন রাউট (/tasks/<task_id>)
@app.route('/tasks/<task_id>')
def task_detail(task_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    user = supabase.table("users").select("username").eq("id", user_id).execute().data[0]
    
    # নির্দিষ্ট টাস্ক আইডি দিয়ে ডাটা কুয়েরি
    task_query = supabase.table("tasks").select("*").eq("id", task_id).execute().data
    if not task_query:
        flash("টাস্কটি খুঁজে পাওয়া যায়নি।", "danger")
        return redirect(url_for('tasks'))
        
    task = task_query[0]
    
    # এই কাজের জন্য পূর্বে কোনো সাবমিশন করা হয়েছে কিনা চেক করা
    submission_query = supabase.table("task_submissions") \
        .select("status, proof_image_url") \
        .eq("user_id", user_id).eq("task_id", task_id).execute().data
        
    status = submission_query[0]['status'] if submission_query else None
    proof_url = submission_query[0]['proof_image_url'] if submission_query else None
    
    return render_template('task_detail.html', task=task, status=status, proof_url=proof_url)


# app.py ফাইলের /tasks/submit-normal রাউটটি এটি দিয়ে পরিবর্তন করুন
@app.route('/tasks/submit-normal', methods=['POST'])
def submit_normal():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    task_id = request.form.get('task_id')
    proof_url = request.form.get('proof_image_url')
    
    # কাজের প্রুফ না থাকলে হোম পেজের বদলে সরাসরি সেই টাস্কের ডিটেইলস পেজেই রিডাইরেক্ট করবে
    if not proof_url:
        flash("দয়া করে কাজের প্রুফ (স্ক্রিনশট) আপলোড করুন।", "danger")
        return redirect(url_for('task_detail', task_id=task_id))
        
    try:
        # Rejected থাকা পূর্ববর্তী ডাটা ডিলিট করে দেওয়া হচ্ছে
        supabase.table("task_submissions").delete() \
            .eq("user_id", user_id).eq("task_id", task_id).eq("status", "Rejected").execute()
        
        # নতুন পেন্ডিং রিকোয়েস্ট ইনসার্ট
        supabase.table("task_submissions").insert({
            "user_id": user_id,
            "task_id": task_id,
            "proof_image_url": proof_url,
            "status": "Pending"
        }).execute()
        flash("কাজের প্রুফ সফলভাবে জমা দেওয়া হয়েছে। এডমিন ভেরিফাই করবে।", "success")
    except Exception:
        flash("এই কাজটি ইতিমধ্যে প্রক্রিয়াধীন (Pending) অথবা অনুমোদিত (Approved) আছে।", "danger")
        
    return redirect(url_for('tasks'))

# app.py ফাইলের /history রাউটটি এটি দিয়ে পরিবর্তন করুন
# (এখানে tasks সম্পর্কের বদলে সুনির্দিষ্ট "tasks:task_id" রিলেশন ম্যাপ করা হয়েছে)
@app.route('/history')
def history():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    deposits = supabase.table("deposits").select("*").eq("user_id", user_id).order("created_at", desc=True).execute().data
    withdrawals = supabase.table("withdrawals").select("*").eq("user_id", user_id).order("created_at", desc=True).execute().data
    
    # শতভাগ নিরাপদ ও নিখুঁত জয়েনিং কুয়েরি
    task_history = supabase.table("task_submissions") \
        .select("proof_image_url, status, created_at, tasks:task_id(title, reward)") \
        .eq("user_id", user_id).order("created_at", desc=True).execute().data or []
    
    transactions = supabase.table("transactions") \
        .select("*") \
        .eq("user_id", user_id) \
        .order("created_at", desc=True).execute().data or []

    today_income = 0.00
    yesterday_income = 0.00
    total_income = 0.00
    
    for tx in transactions:
        amount = float(tx['amount'])
        tx_date = datetime.datetime.fromisoformat(tx['created_at'].replace('Z', '+00:00'))
        
        if amount > 0:
            total_income += amount
            if tx_date >= today_start if 'today_start' in locals() else now.replace(hour=0, minute=0, second=0, microsecond=0) if 'now' in locals() else datetime.datetime.now(datetime.timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0):
                today_income += amount
            elif (yesterday_start if 'yesterday_start' in locals() else today_start - datetime.timedelta(days=1)) <= tx_date < (yesterday_end if 'yesterday_end' in locals() else today_start):
                yesterday_income += amount
                
    # টাইমস্ট্যাম্প ডেট ক্যালকুলেশন ফিক্সড সেফটি ব্লক
    now = datetime.datetime.now(datetime.timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - datetime.timedelta(days=1)
    yesterday_end = today_start
    
    today_income = 0.00
    yesterday_income = 0.00
    total_income = 0.00
    
    for tx in transactions:
        amount = float(tx['amount'])
        tx_date = datetime.datetime.fromisoformat(tx['created_at'].replace('Z', '+00:00'))
        
        if amount > 0:
            total_income += amount
            if tx_date >= today_start:
                today_income += amount
            elif yesterday_start <= tx_date < yesterday_end:
                yesterday_income += amount

    return render_template('history.html', 
                           transactions=transactions, 
                           withdrawals=withdrawals, 
                           task_history=task_history,
                           today_income=round(today_income, 2),
                           yesterday_income=round(yesterday_income, 2),
                           total_income=round(total_income, 2))
    
@app.route('/admin/user-action', methods=['POST'])
def admin_user_action():
    if not check_admin_auth():
        return "Unauthorized Action", 403
        
    target_id = request.form.get('user_id')
    action = request.form.get('action')
    
    if action == 'ban':
        supabase.table("users").update({"is_banned": True}).eq("id", target_id).execute()
        flash("ইউজার অ্যাকাউন্ট সাময়িকভাবে স্থগিত (Banned) করা হয়েছে।", "success")
        
    elif action == 'unban':
        supabase.table("users").update({"is_banned": False}).eq("id", target_id).execute()
        flash("ইউজার অ্যাকাউন্ট পুনরায় সক্রিয় (Unbanned) করা হয়েছে।", "success")
        
    elif action == 'delete':
        supabase.table("users").delete().eq("id", target_id).execute()
        flash("ইউজার ডাটাবেজ থেকে সম্পূর্ণ মুছে ফেলা হয়েছে।", "success")
        
    elif action == 'add_balance':
        amount = float(request.form.get('amount', 0))
        supabase.rpc("increment_balance", {"user_id": target_id, "amount": amount}).execute()
        flash(f"সফলভাবে {amount} টাকা যোগ করা হয়েছে।", "success")
        
    elif action == 'add_referral':
        supabase.table("referrals").insert({
            "referrer_id": target_id,
            "status": "Success",
            "scheduled_payout_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }).execute()
        
        supabase.rpc("increment_balance", {"user_id": target_id, "amount": 30.00}).execute()
        flash("ম্যানুয়ালি ১টি সফল রেফারেল এবং ৩০ টাকা যোগ করা হয়েছে।", "success")
        
    return redirect(url_for('admin_dashboard'))


# (অন্যান্য এডমিন রাউটের সাথে নিচের নতুন রাউটটি যুক্ত করুন)

@app.route('/admin/user-search')
def admin_user_search():
    if not check_admin_auth():
        return "Unauthorized Access", 403
        
    query = request.args.get('query', '').strip()
    target_user = None
    task_history = []
    withdraw_history = []
    referrals_history = []
    
    if query:
        try:
            # ১. ইউআইডি (UID) অথবা ইমেইল দিয়ে সার্চ করা হচ্ছে
            if query.isdigit():
                u_query = supabase.table("users").select("*").eq("uid", int(query)).execute().data
            else:
                u_query = supabase.table("users").select("*").ilike("email", f"%{query}%").execute().data
                
            if u_query:
                target_user = u_query[0]
                target_id = target_user['id']
                
                # ক. এই ইউজারের টাস্ক সাবমিশন হিস্ট্রি (কাজের নাম ও রিওয়ার্ড সহ)
                task_history = supabase.table("task_submissions") \
                    .select("id, status, proof_image_url, created_at, tasks(title, reward)") \
                    .eq("user_id", target_id).order("created_at", desc=True).execute().data or []
                    
                # খ. এই ইউজারের উইথড্রয়াল হিস্ট্রি (সাধারণ ও এজেন্ট উভয় ক্যাটাগরি)
                withdraw_history = supabase.table("withdrawals") \
                    .select("*") \
                    .eq("user_id", target_id).order("created_at", desc=True).execute().data or []
                    
                # গ. এই ইউজারের রেফারেল হিস্ট্রি এবং রেফার করা মেম্বারদের লাইভ ডাটাবেজ ব্যালেন্স
                referrals_history = supabase.table("referrals") \
                    .select("status, created_at, users:referred_id(username, email, uid, balance)") \
                    .eq("referrer_id", target_id).order("created_at", desc=True).execute().data or []
        except Exception as e:
            print("Admin User Audit Error:", e)
            
    return render_template('admin_user_audit.html',
                           target_user=target_user,
                           task_history=task_history,
                           withdraw_history=withdraw_history,
                           referrals_history=referrals_history,
                           query=query)
    
@app.route('/tasks/claim-one-time', methods=['POST'])
def claim_one_time():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
    task_name = request.json.get('task_name')
    user = supabase.table("users").select("*").eq("id", user_id).execute().data[0]
    
    exists = supabase.table("user_one_time_tasks").select("id").eq("user_id", user_id).eq("task_name", task_name).execute().data
    if exists:
        return jsonify({"status": "error", "message": "এই টাস্কটি ইতিমধ্যে ক্লেইম করা হয়েছে।"})
        
    reward = 0.00
    
    success_refs_query = supabase.table("referrals").select("id").eq("referrer_id", user_id).eq("status", "Success").execute().data
    success_ref_count = len(success_refs_query)
    
    if task_name == 'profile_update':
        if user.get('phone_number') and user.get('age') and user.get('district'):
            reward = 5.00
        else:
            return jsonify({"status": "error", "message": "আপনার প্রোফাইলের সব তথ্য এখনও পূর্ণ করা হয়নি।"})
            
    elif task_name == 'join_channel':
        reward = 5.00
        
    elif task_name == 'watch_tutorial':
        reward = 5.00
        
    elif task_name == 'refer_3':
        if success_ref_count >= 3:
            reward = 50.00
        else:
            return jsonify({"status": "error", "message": "আপনার এখনো ৩টি সফল রেফারেল সম্পন্ন হয়নি।"})
            
    elif task_name == 'refer_10':
        if success_ref_count >= 10:
            reward = 150.00
        else:
            return jsonify({"status": "error", "message": "আপনার এখনো ১০টি সফল রেফারেল সম্পন্ন হয়নি।"})
    else:
        return jsonify({"status": "error", "message": "অবৈধ টাস্ক রিকোয়েস্ট।"})
        
    supabase.rpc("increment_balance", {"user_id": user_id, "amount": reward}).execute()
    supabase.table("user_one_time_tasks").insert({"user_id": user_id, "task_name": task_name}).execute()
    
    supabase.table("transactions").insert({
        "user_id": user_id,
        "title": f"One-Time Task Completed: {task_name.replace('_', ' ').title()}",
        "amount": reward
    }).execute()
    
    return jsonify({"status": "success", "message": f"সফলভাবে ক্লেইমড! আপনার ব্যালেন্সে ৳ {reward} যোগ করা হয়েছে। "})


@app.route('/admin/add', methods=['GET', 'POST'])
def admin_add_task():
    if not check_admin_auth():
        return "Unauthorized Access", 403
        
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        link = request.form.get('link')
        reward = float(request.form.get('reward'))
        
        supabase.table("tasks").insert({
            "title": title,
            "description": description,
            "link": link,
            "reward": reward
        }).execute()
        flash("নতুন নরমাল টাস্কটি সফলভাবে ডাটাবেজে যুক্ত হয়েছে।", "success")
        return redirect(url_for('admin_add_task'))
        
    pending_submissions = supabase.table("task_submissions") \
        .select("id, proof_image_url, status, created_at, users(username, email), tasks(title, reward)") \
        .eq("status", "Pending").execute().data
        
    return render_template('admin_add.html', pending_submissions=pending_submissions)


@app.route('/admin/task-action', methods=['POST'])
def admin_task_action():
    if not check_admin_auth():
        return "Unauthorized Action", 403
        
    submission_id = request.form.get('submission_id')
    action = request.form.get('action')
    
    submission = supabase.table("task_submissions").select("*, tasks(reward)").eq("id", submission_id).execute().data
    if not submission:
        flash("সাবমিশন ডাটা পাওয়া যায়নি।", "danger")
        return redirect(url_for('admin_add_task'))
        
    sub = submission[0]
    user_id = sub['user_id']
    reward = float(sub['tasks']['reward'])
    
    if action == 'approve':
        supabase.table("task_submissions").update({"status": "Approved"}).eq("id", submission_id).execute()
        supabase.rpc("increment_balance", {"user_id": user_id, "amount": reward}).execute()
        flash("টাস্ক সাবমিশন এপ্রুভ এবং ইউজারকে রিওয়ার্ড দেওয়া হয়েছে।", "success")
    elif action == 'reject':
        supabase.table("task_submissions").update({"status": "Rejected"}).eq("id", submission_id).execute()
        flash("টাস্ক সাবমিশন বাতিল (Rejected) করা হয়েছে।", "success")
        
    return redirect(url_for('admin_add_task'))


@app.route('/')
def home():
    user_id = session.get('user_id')
    user = None
    if user_id:
        try:
            user_data = supabase.table("users").select("username", "uid").eq("id", user_id).execute().data
            if user_data:
                user = user_data[0]
        except Exception:
            pass
    return render_template('home.html', user=user)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user_query = supabase.table("users").select("*").eq("email", email).execute()
        
        if user_query.data:
            user = user_query.data[0]
            
            if user.get('is_banned'):
                flash("আপনার অ্যাকাউন্টটি সাময়িকভাবে স্থগিত (Banned) করা হয়েছে।", "danger")
                return render_template('login.html')
                
            if check_password_hash(user['password_hash'], password):
                session.permanent = True
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['uid'] = user['uid']
                
                now = datetime.datetime.now(datetime.timezone.utc).isoformat()
                supabase.table("users").update({"last_login": now}).eq("id", user['id']).execute()
                
                return redirect(url_for('dashboard'))
            
        flash("ভুল ইমেইল অথবা পাসওয়ার্ড।", "danger")
    return render_template('login.html')
    
    
@app.route('/withdraw', methods=['GET', 'POST'])
def withdraw():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    user = supabase.table("users").select("*").eq("id", user_id).execute().data[0]
    balance = float(user['balance'])
    
    success_refs_query = supabase.table("referrals") \
        .select("id") \
        .eq("referrer_id", user_id) \
        .eq("status", "Success") \
        .execute().data
    success_ref_count = len(success_refs_query)
    
    meets_referral_cond = (success_ref_count >= 3)
    meets_balance_cond = (balance >= 400.00)
    can_withdraw = (meets_referral_cond and meets_balance_cond)
    
    if request.method == 'POST':
        amount = float(request.form.get('amount'))
        method = request.form.get('method')
        number = request.form.get('number')
        
        if not can_withdraw:
            flash("উইথড্র করার শর্তসমূহ পূরণ হয়নি।", "danger")
        elif amount < 400.00:
            flash("সর্বনিম্ন উইথড্রয়াল পরিমাণ ৪০০ টাকা।", "danger")
        elif amount > balance:
            flash("আপনার অ্যাকাউন্টে পর্যাপ্ত ব্যালেন্স নেই।", "danger")
        else:
            supabase.rpc("increment_balance", {"user_id": user_id, "amount": -amount}).execute()
            
            supabase.table("withdrawals").insert({
                "user_id": user_id,
                "amount": amount,
                "payment_method": method,
                "payment_number": number,
                "status": "Pending"
            }).execute()
            
            flash("উইথড্রয়াল অনুরোধ সফলভাবে সাবমিট হয়েছে।", "success")
            return redirect(url_for('withdraw'))
            
    history = supabase.table("withdrawals").select("*").eq("user_id", user_id).order("created_at", desc=True).execute().data
    
    return render_template('withdrawal.html', 
                           user=user, 
                           balance=balance,
                           success_ref_count=success_ref_count,
                           meets_referral_cond=meets_referral_cond,
                           meets_balance_cond=meets_balance_cond,
                           can_withdraw=can_withdraw,
                           history=history)
    
    

@app.route('/store')
def store():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    user = supabase.table("users").select("balance").eq("id", user_id).execute().data[0]
    premium_pkgs = supabase.table("packages").select("*").eq("is_premium", True).order("cost", desc=False).execute().data
    
    deposit_history = supabase.table("deposits").select("*").eq("user_id", user_id).order("created_at", desc=True).execute().data
    
    purchase_history = supabase.table("user_packages") \
        .select("bought_at, packages(name, cost, is_premium)") \
        .eq("user_id", user_id).order("bought_at", desc=True).execute().data
    
    return render_template('store.html', 
                           balance=user['balance'], 
                           premium_packages=premium_pkgs,
                           deposit_history=deposit_history,
                           purchase_history=purchase_history)    
    
@app.route('/add-money', methods=['GET', 'POST'])
def add_money():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        amount = request.form.get('amount')
        method = request.form.get('method')
        tx_id = request.form.get('transaction_id')
        
        try:
            supabase.table("deposits").insert({
                "user_id": user_id,
                "amount": float(amount),
                "payment_method": method,
                "transaction_id": tx_id,
                "status": "Pending"
            }).execute()
            flash("অনুরোধ জমা হয়েছে। যাচাইকরণের পর ব্যালেন্স যোগ করা হবে।", "success")
        except Exception:
            flash("এই ট্রানজেকশন আইডিটি পূর্বে ব্যবহৃত হয়েছে।", "danger")
            
    history = supabase.table("deposits").select("*").eq("user_id", user_id).order("created_at", desc=True).execute().data
    return render_template('add_money.html', history=history)

# app.py ফাইলের /register রাউটটি এটি দিয়ে পরিবর্তন করুন
# (এখানে আইপি ব্লকিং নেই, তবে একই ডিভাইস দিয়ে নিজের লিংকে অ্যাকাউন্ট খোলা সম্পূর্ণ লকড থাকবে)
@app.route('/register', methods=['GET', 'POST'])
def register():
    ref_by = request.args.get('ref', '')
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        referrer_code = request.form.get('referrer')
        device_fingerprint = request.form.get('device_fingerprint')
        device_name = request.form.get('device_name')

        ip_address = request.headers.get('x-forwarded-for', request.remote_addr)
        if ip_address:
            ip_address = ip_address.split(',')[0].strip()

        hashed_password = generate_password_hash(password)
        initial_balance = 0.00
        referrer_id = None
        referrer_device_name = None
        referrer_fingerprint = None

        if referrer_code and referrer_code.isdigit():
            ref_uid = int(referrer_code)
            referrer_res = supabase.table("users").select("id", "device_name", "device_fingerprint").eq("uid", ref_uid).execute()
            if referrer_res.data:
                referrer_id = referrer_res.data[0]['id']
                referrer_device_name = referrer_res.data[0].get('device_name')
                referrer_fingerprint = referrer_res.data[0].get('device_fingerprint')
                initial_balance = 50.00 # নতুন মেম্বার পাবেন ৫০ টাকা বোনাস

        # --- কঠোর একই ডিভাইস সেলফ-রেফারেল ব্লকার (WebGL + ThumbmarkJS চেক) ---
        if referrer_id:
            # ক. জিপিইউ ড্রাইভার ও ফিজিক্যাল ডিভাইস মডেল ম্যাচিং চেক
            if referrer_device_name and device_name:
                ref_dev_clean = referrer_device_name.strip().lower()
                my_dev_clean = device_name.strip().lower()
                is_generic_dev = "unknown" in my_dev_clean or "android" in my_dev_clean or "pc" in my_dev_clean
                if not is_generic_dev and ref_dev_clean == my_dev_clean:
                    flash("নিরাপত্তা সতর্কতা: রেফারার এবং আপনার মোবাইল ডিভাইসের মডেল একই হওয়ায় রেজিস্ট্রেশন বাতিল করা হয়েছে।", "danger")
                    return redirect(url_for('register', ref=ref_by))

            # খ. ThumbmarkJS লাইব্রেরি জেনারেটেড ডিভাইস ফিঙ্গারপ্রিন্ট ম্যাচিং চেক
            if referrer_fingerprint and device_fingerprint:
                ref_fp_clean = referrer_fingerprint.strip().lower()
                my_fp_clean = device_fingerprint.strip().lower()
                is_generic_fp = my_fp_clean in ["undefined", "null", "none", ""] or len(my_fp_clean) < 5 or my_fp_clean.startswith("fallback_")
                if not is_generic_fp and ref_fp_clean == my_fp_clean:
                    flash("নিরাপত্তা সতর্কতা: আপনি একই ডিভাইস ব্যবহার করে নিজের রেফারেল লিংকে অ্যাকাউন্ট খুলতে পারবেন না।", "danger")
                    return redirect(url_for('register', ref=ref_by))

        user_data = {
            "username": username,
            "email": email,
            "password_hash": hashed_password,
            "balance": initial_balance,
            "device_fingerprint": device_fingerprint,
            "ip_address": ip_address,
            "device_name": device_name if device_name else "Unknown Device"
        }
        
        try:
            new_user_res = supabase.table("users").insert(user_data).execute()
            if new_user_res.data:
                new_user_id = new_user_res.data[0]['id']
                new_uid = new_user_res.data[0]['uid']
                
                free_expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)
                supabase.table("user_packages").insert({
                    "user_id": new_user_id,
                    "package_id": 1,
                    "expires_at": free_expiry.isoformat()
                }).execute()
                
                if referrer_id:
                    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
                    
                    if random.random() < 0.80:
                        status = "Success"
                        supabase.rpc("increment_balance", {"user_id": referrer_id, "amount": 15.00}).execute()
                        
                        supabase.table("transactions").insert({
                            "user_id": referrer_id,
                            "title": f"Referral Bonus (New UID: #{new_uid})",
                            "amount": 15.00
                        }).execute()
                    else:
                        status = "Failed"
                        
                    supabase.table("referrals").insert({
                        "referrer_id": referrer_id,
                        "referred_id": new_user_id,
                        "status": status,
                        "scheduled_payout_at": now_str,
                        "processed_at": now_str
                    }).execute()
                        
                flash("নিবন্ধন সফল হয়েছে। লগইন করুন।", "success")
                return redirect(url_for('login'))
        except Exception:
            flash("ইউজারনেম অথবা ইমেইলটি ইতিমধ্যে ব্যবহৃত হয়েছে।", "danger")
            
    return render_template('register.html', ref_by=ref_by)
    
@app.route('/claim-daily', methods=['POST'])
def claim_daily():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
    try:
        user_query = supabase.table("users").select("last_daily_checkin").eq("id", user_id).execute()
        if not user_query.data:
            return jsonify({"status": "error", "message": "ব্যবহারকারী সনাক্ত করা যায়নি।"}), 404
            
        user = user_query.data[0]
        last_checkin_str = user.get('last_daily_checkin')
        
        now = datetime.datetime.now(datetime.timezone.utc)
        reward_amount = 5.00
        
        if last_checkin_str:
            last_checkin = datetime.datetime.fromisoformat(last_checkin_str.replace('Z', '+00:00'))
            cooldown = datetime.timedelta(hours=24)
            
            if now < last_checkin + cooldown:
                return jsonify({
                    "status": "error", 
                    "message": "আপনি ইতিমধ্যে আজকের ডেইলি বোনাস ক্লেইম করেছেন।"
                }), 400

        supabase.table("users").update({"last_daily_checkin": now.isoformat()}).eq("id", user_id).execute()
        supabase.rpc("increment_balance", {"user_id": user_id, "amount": reward_amount}).execute()
        
        supabase.table("transactions").insert({
            "user_id": user_id,
            "title": "Daily Check-in Bonus claimed",
            "amount": reward_amount
        }).execute()
        
        return jsonify({
            "status": "success", 
            "message": f"ডেইলি চেক-ইন সফল! আপনার ব্যালেন্সে ৳ {reward_amount} যোগ করা হয়েছে।"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": f"ডাটাবেজ ত্রুটি: {str(e)}"}), 500
        
# (অন্যান্য কোড অপরিবর্তিত থাকবে, কেবল /dashboard রাউটটি নিচের কোড দ্বারা প্রতিস্থাপন করুন)
# app.py ফাইলের ড্যাশবোর্ড রাউটটি নিচের কোড দ্বারা সম্পূর্ণ আপডেট করে নিন:
@app.route('/dashboard')
def dashboard():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # মেয়াদোত্তীর্ণ প্যাকেজ ডিলিট (নিরাপদ চেকিং)
    try:
        supabase.table("user_packages").delete().eq("user_id", user_id).not_.is_("expires_at", "null").lt("expires_at", now.isoformat()).execute()
    except Exception:
        pass
        
    user = supabase.table("users").select("*").eq("id", user_id).execute().data[0]
    balance = float(user['balance'])
    
    # ডেইলি চেক-ইন ভ্যালিডেশন
    is_daily_eligible = True
    last_checkin_str = user.get('last_daily_checkin')
    if last_checkin_str:
        last_checkin = datetime.datetime.fromisoformat(last_checkin_str.replace('Z', '+00:00'))
        cooldown = datetime.timedelta(hours=24)
        if now < last_checkin + cooldown:
            is_daily_eligible = False
    
    # মেয়াদ (expires_at) সহ ইউজারের সক্রিয় প্যাকেজগুলোর তালিকা রিট্রিভ করা
    all_pkgs = supabase.table("user_packages") \
        .select("id, last_claimed_at, expires_at, packages(name, duration_hours, yield_amount, is_premium)") \
        .eq("user_id", user_id).execute().data or []
        
    # সেলফ-হিলিং কন্ডিশন: যদি ইউজারের কোনো প্যাকেজই সচল না থাকে
    if not all_pkgs:
        free_expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365)
        supabase.table("user_packages").insert({
            "user_id": user_id,
            "package_id": 1,
            "expires_at": free_expiry.isoformat()
        }).execute()
        
        all_pkgs = supabase.table("user_packages") \
            .select("id, last_claimed_at, expires_at, packages(name, duration_hours, yield_amount, is_premium)") \
            .eq("user_id", user_id).execute().data or []

    owned_pkgs = []
    for p in all_pkgs:
        # যদি কোনো প্যাকেজের মূল ইনফরমেশন ডাটাবেজে না পাওয়া যায় তবে ক্র্যাশ এড়াতে স্কিপ করবে
        if not p.get('packages'):
            continue
        owned_pkgs.append(p)
        
    has_premium_pkg = any(p['packages']['is_premium'] for p in owned_pkgs if p.get('packages'))
    success_refs_query = supabase.table("referrals").select("id").eq("referrer_id", user_id).eq("status", "Success").execute().data
    success_ref_count = len(success_refs_query)
    
    ref_progress = 50 if (success_ref_count >= 3 or has_premium_pkg) else min(success_ref_count / 3, 1.0) * 50
    bal_progress = min(balance / 300, 1.0) * 50
    progress_percent = int(ref_progress + bal_progress)

    notice = "Opti Work এ আপনাকে স্বাগতম! ফ্রি মাইনিং চালু করে প্রতি ৮ ঘণ্টায় 7 টাকা ক্লেইম করুন। প্রিমিয়াম প্যাকেজ কিনলে আয় আরও বৃদ্ধি পাবে।"

    return render_template('dashboard.html', 
                           user=user, 
                           owned_packages=owned_pkgs, 
                           notice=notice,
                           progress_percent=progress_percent,
                           is_daily_eligible=is_daily_eligible)
    
@app.route('/buy-package', methods=['POST'])
def buy_package():
    user_id = session.get('user_id')
    package_id = request.form.get('package_id')
    if not user_id:
        return redirect(url_for('login'))
        
    pkg = supabase.table("packages").select("*").eq("id", package_id).execute()
    if not pkg.data:
        flash("প্যাকেজ পাওয়া যায়নি।", "danger")
        return redirect(url_for('store'))
        
    cost = float(pkg.data[0]['cost'])
    pkg_name = pkg.data[0]['name']
    
    user = supabase.table("users").select("balance").eq("id", user_id).execute().data[0]
    balance = float(user['balance'])
    
    if balance >= cost:
        supabase.table("user_packages").delete().eq("user_id", user_id).eq("package_id", 1).execute()
        
        supabase.rpc("increment_balance", {"user_id": user_id, "amount": -cost}).execute()
        
        expiry_date = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)
        
        supabase.table("user_packages").insert({
            "user_id": user_id,
            "package_id": package_id,
            "last_claimed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "expires_at": expiry_date.isoformat()
        }).execute()
        
        flash(f"{pkg_name} প্যাকেজটি সফলভাবে সক্রিয় করা হয়েছে। মেয়াদ ৩০ দিন।", "success")
    else:
        shortage = cost - balance
        flash(f"ব্যালেন্স অপর্যাপ্ত! {pkg_name} প্যাকেজটি কিনতে আপনার আরও ৳ {shortage:.2f} লাগবে। দয়া করে এড মানি করুন।", "danger")
        
    return redirect(url_for('store'))
@app.route('/claim-mining', methods=['POST'])
def claim_mining():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
    user_package_id = request.json.get('user_package_id')
    if not user_package_id:
        return jsonify({"status": "error", "message": "অবৈধ মাইনিং রিকোয়েস্ট।"}), 400
        
    pkg_query = supabase.table("user_packages") \
        .select("id, last_claimed_at, expires_at, packages(name, yield_amount, duration_hours)") \
        .eq("id", user_package_id).eq("user_id", user_id).execute().data
        
    if not pkg_query:
        return jsonify({"status": "error", "message": "প্যাকেজটি পাওয়া যায়নি বা মেয়াদ শেষ হয়ে গেছে।"}), 404
        
    record = pkg_query[0]
    now = datetime.datetime.now(datetime.timezone.utc)
    
    if record.get('expires_at'):
        expires_at = datetime.datetime.fromisoformat(record['expires_at'].replace('Z', '+00:00'))
        if now > expires_at:
            supabase.table("user_packages").delete().eq("id", user_package_id).execute()
            return jsonify({"status": "error", "message": "এই মাইনিং packagesটির মেয়াদ শেষ হয়ে গেছে।"}), 400
            
    last_claim = datetime.datetime.fromisoformat(record['last_claimed_at'].replace('Z', '+00:00'))
    cooldown = datetime.timedelta(hours=record['packages']['duration_hours'])
    
    if now >= last_claim + cooldown:
        supabase.table("user_packages").update({"last_claimed_at": now.isoformat()}).eq("id", user_package_id).execute()
        yield_amount = float(record['packages']['yield_amount'])
        
        supabase.rpc("increment_balance", {"user_id": user_id, "amount": yield_amount}).execute()
        
        supabase.table("transactions").insert({
            "user_id": user_id,
            "title": f"Mining Yield Claimed: {record['packages']['name']}",
            "amount": yield_amount
        }).execute()
        
        return jsonify({"status": "success", "message": f"৳ {yield_amount} সফলভাবে ক্লেইমড!"})
    else:
        return jsonify({"status": "error", "message": "এই নোডের মাইনিং প্রসেস এখনও সম্পন্ন হয়নি।"})


# ৮. লগআউট
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
