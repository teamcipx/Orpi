import os
import datetime
import random
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from supabase import create_client, Client
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
# প্রোডাকশনে ব্যবহারের জন্য সেশন সিক্রেট কি পরিবর্তন করুন
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "super_secret_key_change_me")

# Supabase API কানেকশন সেটিংস
SUPABASE_URL = os.environ.get("SUPABASE_URL", "YOUR_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "YOUR_SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ইমেইল মাস্ক করার ফিল্টার (যেমন: ab***c@domain.com)
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

# (লগইন রাউটে নিচের মতো ব্যানড চেক যুক্ত করুন)
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user_query = supabase.table("users").select("*").eq("email", email).execute()
        
        if user_query.data:
            user = user_query.data[0]
            
            # অ্যাকাউন্ট ব্যানড করা আছে কিনা যাচাই করা
            if user.get('is_banned'):
                flash("আপনার অ্যাকাউন্টটি সাময়িকভাবে স্থগিত (Banned) করা হয়েছে।", "danger")
                return render_template('login.html')
                
            if check_password_hash(user['password_hash'], password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                
                now = datetime.datetime.now(datetime.timezone.utc).isoformat()
                supabase.table("users").update({"last_login": now}).eq("id", user['id']).execute()
                
                return redirect(url_for('dashboard'))
            
        flash("ভুল ইমেইল অথবা পাসওয়ার্ড।", "danger")
    return render_template('login.html')


# ------------------ এডমিন প্যানেল রাউটসমূহ ------------------

# এডমিন ভেরিফিকেশন হেল্পার
def check_admin_auth():
    user_id = session.get('user_id')
    if not user_id:
        return None
    user = supabase.table("users").select("is_admin, is_banned").eq("id", user_id).execute().data
    if user and user[0]['is_admin'] and not user[0]['is_banned']:
        return user_id
    return None

@app.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    if not check_admin_auth():
        return "Unauthorized Access", 403
        
    now = datetime.datetime.now(datetime.timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    
    # ১. মেট্রিক্স বা স্ট্যাটিস্টিকস হিসাব করা
    # মোট ইউজার সংখ্যা
    all_users = supabase.table("users").select("id", count="exact").execute()
    total_users = all_users.count if all_users.count is not None else 0
    
    # আজকের নতুন ইউজার সংখ্যা
    today_users_query = supabase.table("users").select("id", count="exact").gte("created_at", today_start).execute()
    today_users = today_users_query.count if today_users_query.count is not None else 0
    
    # মোট ডিপোজিট (অনুমোদিত/Approved)
    total_dep_query = supabase.table("deposits").select("amount").eq("status", "Approved").execute().data
    total_deposits = sum(float(d['amount']) for d in total_dep_query)
    
    # আজকের মোট ডিপোজিট
    today_dep_query = supabase.table("deposits").select("amount").eq("status", "Approved").gte("created_at", today_start).execute().data
    today_deposits = sum(float(d['amount']) for d in today_dep_query)
    
    # ২. ইউজার সার্চ ইঞ্জিন
    search_query = request.args.get('search', '').strip()
    users_list = []
    
    if search_query:
        # ইমেইল অথবা ইউজারনেম দিয়ে সার্চ
        u_data = supabase.table("users").select("id, username, email, balance, is_banned") \
            .or_(f"email.ilike.%{search_query}%,username.ilike.%{search_query}%").execute().data
        users_list = u_data
    else:
        # ডিফল্টভাবে শেষ ১০ জন ইউজার প্রদর্শন করা
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
        # একটি ডামি রেফারেল যুক্ত করা যা সরাসরি 'Success' স্ট্যাটাস পাবে (রেফারেল বাড়ানোর জন্য)
        supabase.table("referrals").insert({
            "referrer_id": target_id,
            "status": "Success",
            "scheduled_payout_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }).execute()
        
        # সফল রেফারেল এর জন্য ৩০ টাকা বোনাস দেওয়া
        supabase.rpc("increment_balance", {"user_id": target_id, "amount": 30.00}).execute()
        flash("ম্যানুয়ালি ১টি সফল রেফারেল এবং ৩০ টাকা যোগ করা হয়েছে।", "success")
        
    return redirect(url_for('admin_dashboard'))
    
# (অন্যান্য কোড অপরিবর্তিত থাকবে, উইথড্রয়াল সম্পর্কিত নতুন রাউটটি নিচে যুক্ত করুন)

@app.route('/withdraw', methods=['GET', 'POST'])
def withdraw():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    # ১. ইউজারের ব্যালেন্স এবং তথ্য নেওয়া
    user = supabase.table("users").select("*").eq("id", user_id).execute().data[0]
    balance = float(user['balance'])
    
    # ২. সফল রেফারেলের সংখ্যা বের করা (status = 'Success')
    success_refs_query = supabase.table("referrals") \
        .select("id") \
        .eq("referrer_id", user_id) \
        .eq("status", "Success") \
        .execute().data
    success_ref_count = len(success_refs_query)
    
    # ৩. শর্তসমূহ পরীক্ষা
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
            # ব্যালেন্স বিয়োগ করা
            supabase.rpc("increment_balance", {"user_id": user_id, "amount": -amount}).execute()
            
            # উইথড্রয়াল রিকোয়েস্ট তৈরি
            supabase.table("withdrawals").insert({
                "user_id": user_id,
                "amount": amount,
                "payment_method": method,
                "payment_number": number,
                "status": "Pending"
            }).execute()
            
            flash("উইথড্রয়াল অনুরোধ সফলভাবে সাবমিট হয়েছে।", "success")
            return redirect(url_for('withdraw'))
            
    # ইউজারের নিজস্ব উইথড্রয়াল হিস্ট্রি রিট্রিভ করা
    history = supabase.table("withdrawals").select("*").eq("user_id", user_id).order("created_at", desc=True).execute().data
    
    return render_template('withdrawal.html', 
                           user=user, 
                           balance=balance,
                           success_ref_count=success_ref_count,
                           meets_referral_cond=meets_referral_cond,
                           meets_balance_cond=meets_balance_cond,
                           can_withdraw=can_withdraw,
                           history=history)
    
@app.route('/register', methods=['GET', 'POST'])
def register():
    ref_by = request.args.get('ref', '')
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        referrer_name = request.form.get('referrer')

        hashed_password = generate_password_hash(password)
        
        # ডিফল্ট ব্যালেন্স ০ টাকা (যদি কোনো রেফারেল না থাকে)
        initial_balance = 0.00
        referrer_id = None

        # রেফারার ইউজারনেম ডাটাবেজে সঠিক কিনা তা যাচাই করা
        if referrer_name:
            referrer_res = supabase.table("users").select("id").eq("username", referrer_name).execute()
            if referrer_res.data:
                referrer_id = referrer_res.data[0]['id']
                initial_balance = 100.00  # রেফারেল লিংকে আসলে কেবল ১০০ টাকা বোনাস পাবেন
        
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
                
                # ডিফল্ট ফ্রি প্যাকেজ অ্যাসাইন করা
                supabase.table("user_packages").insert({
                    "user_id": new_user_id,
                    "package_id": 1
                }).execute()
                
                # যদি রেফারার আইডি ভ্যালিড থাকে, তবে রেফারেল ট্র্যাকিং টেবিল আপডেট করা
                if referrer_id:
                    random_hours = random.randint(48, 62)
                    scheduled_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=random_hours)
                    
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
    
# ৩. ড্যাশবোর্ড রাউট
@app.route('/dashboard')
def dashboard():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    user = supabase.table("users").select("*").eq("id", user_id).execute().data[0]
    
    # সক্রিয় প্যাকেজ রিট্রিভ
    owned_pkgs = supabase.table("user_packages") \
        .select("last_claimed_at, packages(name, duration_hours, yield_amount)") \
        .eq("user_id", user_id).execute().data

    notice = "Opti Work এ আপনাকে স্বাগতম! ফ্রি মাইনিং চালু করে প্রতি ৮ ঘণ্টায় ৭ টাকা ক্লেইম করুন। প্রিমিয়াম প্যাকেজ কিনলে আয় আরও বৃদ্ধি পাবে।"

    return render_template('dashboard.html', user=user, owned_packages=owned_pkgs, notice=notice)

# ৪. স্টোর রাউট (প্যাকেজ শপ)
@app.route('/store')
def store():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    user = supabase.table("users").select("balance").eq("id", user_id).execute().data[0]
    premium_pkgs = supabase.table("packages").select("*").eq("is_premium", True).execute().data
    
    return render_template('store.html', balance=user['balance'], premium_packages=premium_pkgs)

@app.route('/buy-package', methods=['POST'])
def buy_package():
    user_id = session.get('user_id')
    package_id = request.form.get('package_id')
    if not user_id:
        return redirect(url_for('login'))
        
    pkg = supabase.table("packages").select("*").eq("id", package_id).execute()
    if not pkg.data:
        flash("প্যাকেজটি পাওয়া যায়নি।", "danger")
        return redirect(url_for('store'))
        
    cost = float(pkg.data[0]['cost'])
    user = supabase.table("users").select("balance").eq("id", user_id).execute().data[0]
    balance = float(user['balance'])
    
    if balance >= cost:
        # ব্যালেন্স কর্তন করা
        supabase.rpc("increment_balance", {"user_id": user_id, "amount": -cost}).execute()
        
        # ইউজার প্যাকেজ যুক্ত করা
        supabase.table("user_packages").insert({
            "user_id": user_id,
            "package_id": package_id,
            "last_claimed_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }).execute()
        
        flash("প্যাকেজটি সফলভাবে সক্রিয় করা হয়েছে।", "success")
    else:
        flash("আপনার অ্যাকাউন্টে পর্যাপ্ত ব্যালেন্স নেই।", "danger")
        
    return redirect(url_for('store'))

# ৫. রিচার্জ বা অ্যাড মানি রাউট
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

# ৬. রেফারেল রাউট (অন-ডিমান্ড চেকসহ)
@app.route('/referrals')
def referrals():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    now = datetime.datetime.now(datetime.timezone.utc)
    user = supabase.table("users").select("username").eq("id", user_id).execute().data[0]
    
    # অন-ডিমান্ড রেফারেল সময় ও শর্ত পরীক্ষা
    due_referrals = supabase.table("referrals") \
        .select("id, referred_id") \
        .eq("referrer_id", user_id) \
        .eq("status", "Processing") \
        .lte("scheduled_payout_at", now.isoformat()) \
        .execute().data

    for ref in due_referrals:
        referred_id = ref['referred_id']
        ref_user = supabase.table("users").select("last_login").eq("id", referred_id).execute().data
        
        if ref_user:
            last_login_str = ref_user[0]['last_login']
            last_login = datetime.datetime.fromisoformat(last_login_str.replace('Z', '+00:00'))
            twelve_hours_ago = now - datetime.timedelta(hours=12)
            
            # ১২ ঘণ্টার মধ্যে ড্যাশবোর্ড ভিজিট করলে Success অন্যথায় Failed
            new_status = "Success" if last_login >= twelve_hours_ago else "Failed"
            
            # নিরাপদ প্রসেস রেফারেল ফাংশন কল
            supabase.rpc("process_referral_payout", {
                "p_referral_id": ref['id'],
                "p_referrer_id": user_id,
                "p_new_status": new_status,
                "p_reward_amount": 30.00
            }).execute()
            
    referrals_data = supabase.table("referrals") \
        .select("status, created_at, users!referrals_referred_id_fkey(username, email)") \
        .eq("referrer_id", user_id).execute().data
        
    ref_link = request.url_root + "register?ref=" + user['username']
    
    return render_template('referrals.html', referrals=referrals_data, ref_link=ref_link)

# ৭. ক্লেইম এপিআই
@app.route('/claim-mining', methods=['POST'])
def claim_mining():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
    owned_pkgs = supabase.table("user_packages") \
        .select("id, last_claimed_at, packages(yield_amount, duration_hours)") \
        .eq("user_id", user_id).execute().data
         
    now = datetime.datetime.now(datetime.timezone.utc)
    total_yield = 0.00
    claimed_any = False

    for item in owned_pkgs:
        last_claimed = datetime.datetime.fromisoformat(item['last_claimed_at'].replace('Z', '+00:00'))
        cooldown = datetime.timedelta(hours=item['packages']['duration_hours'])
        
        if now >= last_claimed + cooldown:
            supabase.table("user_packages").update({"last_claimed_at": now.isoformat()}).eq("id", item['id']).execute()
            total_yield += float(item['packages']['yield_amount'])
            claimed_any = True
            
    if claimed_any:
        supabase.rpc("increment_balance", {"user_id": user_id, "amount": total_yield}).execute()
        return jsonify({"status": "success", "message": f"৳ {total_yield} ব্যালেন্সে যোগ করা হয়েছে।"})
    else:
        return jsonify({"status": "error", "message": "দয়া করে মাইনিং সময় শেষ হওয়া পর্যন্ত অপেক্ষা করুন।"})

# ৮. লগআউট
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
