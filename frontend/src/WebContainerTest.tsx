
import { useEffect, useRef, useState } from 'react';
import type { WebContainer } from '@webcontainer/api';

type BootStatus = 'idle' | 'booting' | 'installing' | 'starting' | 'ready' | 'error';

const DEMO_PROJECT_FILES = {
  'package.json': {
    file: {
      contents: JSON.stringify(
        {
          name: 'webcontainer-demo',
          type: 'module',
          scripts: {
            start: 'node server.js',
          },
          dependencies: {},
        },
        null,
        2
      ),
    },
  },
  'server.js': {
    file: {
      contents: [
        "import http from 'http';",
        '',
        'const server = http.createServer((req, res) => {',
        "  res.writeHead(200, { 'Content-Type': 'text/plain' });",
        "  res.end('WebContainer operationnel: ' + new Date().toISOString());",
        '});',
        '',
        'server.listen(3111, () => {',
        "  console.log('Serveur demo pret sur le port 3111');",
        '});',
      ].join('\n'),
    },
  },
};

function withTimeout<T>(promise: Promise<T>, ms: number, label: string): Promise<T> {
  return Promise.race([
    promise,
    new Promise<T>((_, reject) => {
      setTimeout(() => reject(new Error(`Timeout depasse (${ms}ms) sur: ${label}`)), ms);
    }),
  ]);
}

export default function WebContainerTest() {
  const [status, setStatus] = useState<BootStatus>('idle');
  const [logs, setLogs] = useState<string[]>([]);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const containerRef = useRef<WebContainer | null>(null);
  const hasBootedRef = useRef(false);

  const appendLog = (line: string) => {
    setLogs((prev) => [...prev, line]);
  };

  useEffect(() => {
    if (hasBootedRef.current) return;
    hasBootedRef.current = true;

    appendLog(`crossOriginIsolated: ${window.crossOriginIsolated}`);
    appendLog(`SharedArrayBuffer disponible: ${typeof SharedArrayBuffer !== 'undefined'}`);
    appendLog(`User agent: ${navigator.userAgent}`);

    if (!window.crossOriginIsolated) {
      setStatus('error');
      setErrorMessage(
        "La page n'est pas cross-origin isolated. Verifiez les en-tetes " +
          'Cross-Origin-Embedder-Policy et Cross-Origin-Opener-Policy.'
      );
      return;
    }

    let cancelled = false;

    async function boot() {
      try {
        setStatus('booting');
        appendLog('Import du module @webcontainer/api...');
        const { WebContainer } = await import('@webcontainer/api');
        appendLog('Module importe. Appel de WebContainer.boot()...');

        const instance = await withTimeout(WebContainer.boot(), 20000, 'WebContainer.boot()');
        if (cancelled) return;
        containerRef.current = instance;
        appendLog('WebContainer demarre.');

        await withTimeout(instance.mount(DEMO_PROJECT_FILES), 10000, 'mount()');
        appendLog('Fichiers de projet montes.');

        setStatus('installing');
        appendLog('Installation des dependances (npm install)...');
        const installProcess = await instance.spawn('npm', ['install']);
        const installExitCode = await withTimeout(installProcess.exit, 30000, 'npm install');
        if (installExitCode !== 0) {
          throw new Error(`npm install a echoue (code ${installExitCode}).`);
        }
        appendLog('Dependances installees.');

        setStatus('starting');
        appendLog('Lancement du serveur (npm start)...');
        const startProcess = await instance.spawn('npm', ['start']);
        startProcess.output.pipeTo(
          new WritableStream({
            write(chunk) {
              appendLog(chunk);
            },
          })
        );

        instance.on('server-ready', (_port, url) => {
          if (cancelled) return;
          appendLog(`Serveur pret: ${url}`);
          setPreviewUrl(url);
          setStatus('ready');
        });
      } catch (err) {
        if (cancelled) return;
        const message = err instanceof Error ? err.message : String(err);
        setErrorMessage(message);
        setStatus('error');
        appendLog(`Erreur: ${message}`);
      }
    }

    boot();

    return () => {
      cancelled = true;
      containerRef.current?.teardown();
    };
  }, []);

  return (
    <div style={{ padding: '1.5rem', fontFamily: 'system-ui, sans-serif', maxWidth: 720 }}>
      <h1 style={{ fontSize: '1.4rem', marginBottom: '0.5rem' }}>Test WebContainers</h1>
      <p style={{ color: '#555', marginBottom: '1rem' }}>
        Statut actuel : <strong>{status}</strong>
      </p>

      {errorMessage && (
        <div
          style={{
            background: '#fee2e2',
            color: '#991b1b',
            padding: '0.75rem 1rem',
            borderRadius: 8,
            marginBottom: '1rem',
          }}
        >
          {errorMessage}
        </div>
      )}

      <div
        style={{
          background: '#0f172a',
          color: '#e2e8f0',
          fontFamily: 'monospace',
          fontSize: '0.8rem',
          padding: '1rem',
          borderRadius: 8,
          minHeight: 160,
          maxHeight: 320,
          overflowY: 'auto',
          whiteSpace: 'pre-wrap',
          marginBottom: '1rem',
        }}
      >
        {logs.length === 0 ? 'En attente...' : logs.join('\n')}
      </div>

      {previewUrl && (
        <div>
          <p style={{ marginBottom: '0.5rem', fontWeight: 600 }}>Apercu en direct :</p>
          <iframe
            src={previewUrl}
            title="WebContainer preview"
            style={{ width: '100%', height: 200, border: '1px solid #cbd5e1', borderRadius: 8 }}
          />
        </div>
      )}
    </div>
  );
}
