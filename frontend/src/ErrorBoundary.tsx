import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: string;
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: '' };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: '' };
  }

  componentDidCatch(_error: Error, errorInfo: ErrorInfo) {
    this.setState({ errorInfo: errorInfo.componentStack || '' });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '20px', fontFamily: 'monospace', background: '#fff', color: '#c00', minHeight: '100vh' }}>
          <h1 style={{ color: '#c00' }}>Erreur de l'application</h1>
          <p><strong>{this.state.error?.name}: {this.state.error?.message}</strong></p>
          <pre style={{ whiteSpace: 'pre-wrap', fontSize: '12px', background: '#f4f4f4', padding: '10px' }}>
            {this.state.error?.stack}
          </pre>
          <pre style={{ whiteSpace: 'pre-wrap', fontSize: '12px', background: '#f4f4f4', padding: '10px' }}>
            {this.state.errorInfo}
          </pre>
          <button onClick={() => window.location.href = '/'}>Retour à l'accueil</button>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
