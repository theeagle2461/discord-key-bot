
                    <html>
                      <head>
                        <title>Discord Key Bot</title>
                        <meta name='viewport' content='width=device-width, initial-scale=1'/>
                        <style>
                          :root { --bg:#0b0718; --panel:#120a2a; --muted:#b399ff; --border:#1f1440; --text:#efeaff; --accent:#6c4af2; }
                          * { box-sizing: border-box; }
                          body { margin:0; font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; background: var(--bg); color: var(--text); }
                          header { background: var(--panel); border-bottom:1px solid var(--border); padding: 16px 24px; display:flex; align-items:center; gap:12px; flex-wrap: wrap; }
                          .brand { font-weight:700; letter-spacing:0.3px; margin-right:8px; }
                          a.nav { color: var(--muted); text-decoration:none; padding:8px 12px; border-radius:10px; background:#121a36; border:1px solid #1a2650; }
                          a.nav:hover { background:#19214a; }
                          main { padding: 24px; max-width: 1100px; margin: 0 auto; }
                          .grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap:16px; }
                          .card { background: var(--panel); border:1px solid var(--border); border-radius:14px; padding:18px; }
                          .stat { display:flex; flex-direction:column; gap:4px; }
                          .stat .label { color:#b9c7ff; font-size:12px; text-transform:uppercase; letter-spacing:0.4px; }
                          .stat .value { font-size:28px; font-weight:700; color:#dfe6ff; }
                          .muted { color:#a4b1d6; font-size:14px; }
                          .row { display:flex; gap:16px; align-items:stretch; flex-wrap:wrap; }
                          .actions a { display:inline-block; margin-right:8px; margin-top:8px; color:white; background: var(--accent); padding:10px 12px; border-radius:10px; text-decoration:none; border:1px solid #2049cc; }
                          .actions a:hover { filter: brightness(0.95); }
                          .kgrid { display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap:12px; }
                          .kbox { background:#0b132b; border:1px solid #1c2b5b; padding:14px; border-radius:12px; }
                          .kbox .ttl { color:#b9c7ff; font-size:12px; letter-spacing:0.3px; text-transform:uppercase; }
                          .kbox .num { font-size:22px; font-weight:700; color:#e6edff; }
                          .kbox .sub { font-size:12px; color:#9ab0ff; margin-top:4px; }
                        </style>
                      </head>
                      <body>
                        <header>
                          <div class='brand' style='font-size:28px;font-weight:800;letter-spacing:0.6px'>CS BOT <span style='font-weight:600;color:#b799ff'>made by iris&classical</span></div>
                          <a class='nav' href='/'>Dashboard</a>
                          <a class='nav' href='/keys'>Keys</a>
                          <a class='nav' href='/my'>My Keys</a>
                          <a class='nav' href='/deleted'>Deleted</a>
                          <a class='nav' href='/generate-form'>Generate</a>
                          <a class='nav' href='/backup'>Backup</a>
                        </header>
                        <main>
                          <div class='row'>
                            <div class='card' style='flex:2'>
                              <div class='grid'>
                                <div class='stat card'>
                                  <div class='label'>Total Keys</div>
                                  <div class='value'>3</div>
                                  <div class='muted'>All keys in database</div>
                                </div>
                                <div class='stat card'>
                                  <div class='label'>Active</div>
                                  <div class='value'>3</div>
                                  <div class='muted'>Currently valid</div>
                                </div>
                                <div class='stat card'>
                                  <div class='label'>Revoked</div>
                                  <div class='value'>0</div>
                                  <div class='muted'>Access removed</div>
                                </div>
                                <div class='stat card'>
                                  <div class='label'>Deleted</div>
                                  <div class='value'>0</div>
                                  <div class='muted'>Moved to recycle</div>
                                </div>
                              </div>
                              <div class='actions'>
                                <a href='/keys'>Manage Keys</a>
                                <a href='/generate-form'>Generate Keys</a>
                                <a href='/my'>My Keys</a>
                                <a href='/backup'>Backup</a>
                              </div>
                            </div>
                          </div>
                          <div style='height:16px'></div>
                          <div class='card'>
                            <div class='kgrid'>
                              <div class='kbox'>
                                <div class='ttl'>Daily Keys</div>
                                <div class='num'>3</div>
                                <div class='sub'>Available: 1</div>
                              </div>
                              <div class='kbox'>
                                <div class='ttl'>Weekly Keys</div>
                                <div class='num'>0</div>
                                <div class='sub'>Available: 0</div>
                              </div>
                              <div class='kbox'>
                                <div class='ttl'>Monthly Keys</div>
                                <div class='num'>0</div>
                                <div class='sub'>Available: 0</div>
                              </div>
                              <div class='kbox'>
                                <div class='ttl'>Lifetime Keys</div>
                                <div class='num'>0</div>
                                <div class='sub'>Available: 0</div>
                              </div>
                              <div class='kbox'>
                                <div class='ttl'>General Keys</div>
                                <div class='num'>0</div>
                                <div class='sub'>Available: 0</div>
                              </div>
                            </div>
                            <div class='muted' style='margin-top:10px'>
                              Status: Online • 2025-08-16 14:21:57 • Bot: Retard.
                            </div>
                          </div>
                        </main>
                      </body>
                    </html>
                    