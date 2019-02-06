---
title: Securing Gramex Deployments
prefix: Tip
...

There are many common security vulnerabilities that we need to protect Gramex instances against.

To check if your project is vulnerable, download and run the
[OWASP Zed Attack Proxy](https://www.owasp.org/index.php/OWASP_Zed_Attack_Proxy_Project).
This runs a penetration test on your application and shares a report.

To protect against common vulnerabilities, the quickest way is to [import deploy.yaml](../deploy/#security).
This [deploy.yaml](https://github.com/gramener/gramex/blob/master/gramex/deploy.yaml)
has commonly used security configurations and is bundled as part of Gramex.

For example, it:

1. Disables [cross-site scripting](https://www.owasp.org/index.php/Cross-site_Scripting_(XSS))
2. Prevents [content-sniffing](https://dunnesec.com/category/attacks-defence/content-sniffing/)
3. Prevents [clickjacking](https://www.owasp.org/index.php/Clickjacking)
4. Hides the server name
5. Only allows downloading specific file types
6. Creates a new cookie secret for each host
7. Caches all files privately
