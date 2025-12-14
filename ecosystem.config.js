module.exports = {
  apps: [{
    name: 'Ansieyes',
    script: 'app.py',
    interpreter: 'python3',
    cwd: '/home/ubuntu/Ansieyes',
    env_file: '.env',
    error_file: '/home/ubuntu/logs/err.log',
    out_file: '/home/ubuntu/logs/out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    merge_logs: true,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    instances: 1,
    exec_mode: 'fork'
  }]
};

