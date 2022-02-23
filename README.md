# locker-server
Secure personal area with OAuth2/OpenID Connect storage engine based on secure and stable unified micro-kernel.

# Purpose
Locker is designed to be unified solution to provide secure, fast and reliable Client Area for any application. If you have client area for customers and confidential private data there (such as name, email, home/delivery address, balance, history of orders) - you can implement it with locker.

# Benefits
- It is secure. (see Security chapter)
- It is already developed, so, no cost/time to develop, no bad surprises, no bugs, no vulnerabilities.
- If app is completely consist of public data + private data, often you can develop it completely on locker, without any other backend!
- It is compatible with most (all?) technologies.
- Locker does not require database. But if you want database - you can import/export to db.

# Security
Locker aim is to be 'Secure as an filesystem'. Any code could contain bugs and vulnerabilities and locker too. But vulnerabilities in web applications happens million times more often then vulnerabilities in filesystems. Why? Because filesystems provides small feature, has simple interface (servers in car service station, in hospital or in university - are very different but may use same filesystem code) and it's possible to polish it very well.

Compare it with web applications, which often developed/tested in short time, some developers may have low skills, and each new application is little different from other.

# Locker vs ...
Locker is not an replacement but rather an add-on. You can add locker features to your usual web application based on Django or custom PHP or any other backend.

But if your application has no other special API (only public data + customer data), sometimes you may go without any other backend at all! 

# Example apps
- Notebooks (such as Google Keep or SimpleNote or WorkFlowy)
- Shops (real full-features shops, with customer area, order history etc.)
- Even social applications (like reddit)!

# Quickstart

~~~
# install redis
apt install redis-server

# create virtualenv 
python3 -m venv /opt/venv/locker-server
. /opt/venv/locker-server/bin/activate

# install from pypi
pip3 install locker-server

# alternative: install from github
pip3 install git+https://github.com/yaroslaff/locker-server.git

#### If you dont have valid SSL cert, you may generate self-signed (yes, browser will alert, but you can skip alert). For production
###openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes -subj '/CN=test.locker.lan'

cat > /etc/default/locker-server <<EOF
# locker env file
LOCKER_APPS_PATH=/opt/locker-apps/
LOCKER_LOCAL_CONFIG=/etc/locker/locker-server.yml
LOCKER_DEBUG=1
EOF


# If install to nginx, copy, edit and activate nginx config for sites
cp /opt/venv/locker-server/locker/nginx/locker /etc/nginx/sites-available/
cp /opt/venv/locker-server/locker/nginx/locker-https /etc/nginx/sites-available/
~~~

## Example locker-server.yml
~~~
VENDOR_CREDENTIALS: 
  google:
    # Get your credentials in Google Developers Console
    # https://console.developers.google.com/
    DISCOVERY_URL: https://accounts.google.com/.well-known/openid-configuration
    CLIENT_ID: 123-zzz.apps.googleusercontent.com
    CLIENT_SECRET: zzzzzzzzzzz

# Hostname, pointing to your server
AUTH_HOST: auth.ll.www-security.net
TOPDOMAIN: ll.www-security.net

~~~

## Sudo 
`/etc/sudoers.d/locker`:
~~~
www-data ALL=(ALL) NOPASSWD: /usr/local/bin/certbot
~~~


## Install locker-admin and ws-emit
Install [locker-admin](https://github.com/yaroslaff/locker-admin):
~~~
pip3 install git+https://github.com/yaroslaff/locker-admin
~~~

Install [ws-emit](https://github.com/yaroslaff/ws-emit):
~~~
pip3 install git+https://github.com/yaroslaff/ws-emit

cp ws-emit/contrib/ws-emit.service /etc/systemd/system
# edit this file and ensure it has correct path to ws-emit.py

cp ws-emit/contrib/ws-emit /etc/default/
# edit and set CORS="*"
~~~



## Myapps
Create first app (for myapps)
~~~
mkdir /opt/locker-apps
chown -R www-data:www-data /opt/locker-apps/
sudo -u www-data locker-admin create adm myapps
~~~

record MASTER KEY from output (use it as LOCKER_KEY later).

Clone [locker-myapps](https://github.com/yaroslaff/locker-myapps) to local computer and create .env file with content similar to:
~~~
LOCKER_HOST=myapps-adm.rudev.www-security.net
LOCKER_KEY=123abc123abc123abc...
~~~

ensure locker-admin works from client machine, make simple command like `locker-admin ls`.

Deploy application from local machine to server: `locker-admin deploy`.
