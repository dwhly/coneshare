import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';
import { Button } from '../ui/Button';

export class ViewerErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Failed to load viewer chunk or component:', error, errorInfo);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
    if (this.props.onRetry) {
      this.props.onRetry();
    } else {
      window.location.reload();
    }
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback({ error: this.state.error, retry: this.handleRetry });
      }

      return (
        <div className="flex min-h-[400px] h-full w-full flex-col items-center justify-center p-8 text-center bg-muted/50">
          <div className="w-full max-w-md rounded-2xl bg-card p-8 shadow-xl shadow-foreground/50 dark:shadow-none border border-border text-center animate-fadeIn">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-danger-subtle text-danger ring-8 ring-danger-border">
              <AlertCircle className="h-6 w-6" />
            </div>
            <h3 className="text-lg font-semibold text-foreground">
              {this.props.title || 'Failed to load viewer'}
            </h3>
            <p className="mt-2 text-sm text-muted-foreground">
              {this.props.description || 'A network error occurred while loading this view. This might happen if a new version was deployed or your connection was interrupted.'}
            </p>
            <div className="mt-6">
              <Button
                onClick={this.handleRetry}
                className="inline-flex items-center gap-2"
                variant="default"
              >
                <RefreshCw className="h-4 w-4" />
                Reload
              </Button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
