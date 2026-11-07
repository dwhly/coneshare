import { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { SettingsTabs } from '../components/settings/SettingsTabs';
import { Button } from '../components/ui/Button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../components/ui/Dialog';
import {
  getCloudProviders,
  getCloudConnections,
  deleteCloudConnection,
  getDropboxConnectUrl,
  getGoogleDriveConnectUrl,
  getNextcloudConnectUrl,
} from '../services/api';
import {
  Cloud,
  HardDrive,
  Database,
  RefreshCw,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  Calendar,
  Clock,
} from 'lucide-react';
const PROVIDER_CONFIG = {
  google_drive: {
    displayName: 'Google Drive',
    icon: <HardDrive className="h-8 w-8 text-success" />,
    getConnectUrl: getGoogleDriveConnectUrl,
    descriptionKey: 'settings.publicCloudStorage',
  },
  dropbox: {
    displayName: 'Dropbox',
    icon: <Database className="h-8 w-8 text-info" />,
    getConnectUrl: getDropboxConnectUrl,
    descriptionKey: 'settings.publicCloudStorage',
  },
  nextcloud: {
    displayName: 'Nextcloud',
    icon: <Cloud className="h-8 w-8 text-tag-4" />,
    getConnectUrl: getNextcloudConnectUrl,
    descriptionKey: 'settings.nextcloudDescription',
  },
};

export function IntegrationsSettingsPage() {
  const { t } = useTranslation();
  const [providers, setProviders] = useState([]);
  const [connections, setConnections] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isDisconnecting, setIsDisconnecting] = useState(false);
  const [selectedConnection, setSelectedConnection] = useState(null);
  const isMounted = useRef(true);

  const fetchIntegrations = async () => {
    try {
      const [providersRes, connectionsRes] = await Promise.all([
        getCloudProviders(),
        getCloudConnections(),
      ]);
      if (isMounted.current) {
        setProviders(providersRes.data);
        setConnections(connectionsRes.data);
      }
    } catch (err) {
      console.error(err);
      if (isMounted.current) {
        toast.error(t('settings.settingsUpdateFailed'));
      }
    } finally {
      if (isMounted.current) {
        setIsLoading(false);
      }
    }
  };

  useEffect(() => {
    isMounted.current = true;
    fetchIntegrations();
    return () => {
      isMounted.current = false;
    };
  }, []);

  const handleConnect = async (providerName) => {
    const config = PROVIDER_CONFIG[providerName];
    if (!config) {
      toast.error(t('settings.unsupportedProvider', { provider: providerName }));
      return;
    }
    try {
      const res = await config.getConnectUrl();
      window.location.href = res.data.authorization_url;
    } catch (err) {
      console.error(err);
      toast.error(t('settings.settingsUpdateFailed'));
    }
  };

  const handleDisconnectConfirm = async () => {
    if (!selectedConnection) return;
    setIsDisconnecting(true);
    try {
      await deleteCloudConnection(selectedConnection.id);
      toast.success(t('settings.settingsUpdated'));
      await fetchIntegrations();
      if (isMounted.current) {
        setSelectedConnection(null);
      }
    } catch (err) {
      console.error(err);
      toast.error(t('settings.settingsUpdateFailed'));
    } finally {
      if (isMounted.current) {
        setIsDisconnecting(false);
      }
    }
  };

  const getProviderIcon = (name) => {
    return PROVIDER_CONFIG[name]?.icon || <Cloud className="h-8 w-8 text-muted-foreground" />;
  };

  const getProviderDisplayName = (name) => {
    return PROVIDER_CONFIG[name]?.displayName || name;
  };

  return (
    <div className="p-4 sm:mx-4 sm:pt-8">
      <div className="mx-auto max-w-3xl">
        <h1 className="text-2xl font-bold mb-6">{t('settings.title')}</h1>
        <SettingsTabs />

        {isLoading ? (
          <div className="flex h-64 items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-info" />
          </div>
        ) : (
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-medium text-foreground">{t('settings.cloudIntegrationsTitle')}</h2>
            <p className="text-sm text-muted-foreground mt-1">
              {t('settings.cloudIntegrationsSubtitle')}
            </p>
          </div>

          <div className="grid gap-6">
            {providers.map((provider) => {
              const connection = connections.find((c) => c.provider === provider.name);
              const isConnected = !!connection;

              return (
                <Card key={provider.name} className="overflow-hidden border border-border shadow-sm transition-all duration-200 hover:shadow-md">
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
                    <div className="flex items-center gap-3">
                      {getProviderIcon(provider.name)}
                      <div>
                        <CardTitle className="text-base font-semibold">
                          {getProviderDisplayName(provider.name)}
                        </CardTitle>
                        <CardDescription className="text-xs">
                          {PROVIDER_CONFIG[provider.name]?.descriptionKey
                            ? t(PROVIDER_CONFIG[provider.name].descriptionKey)
                            : t('settings.cloudStorageProvider')}
                        </CardDescription>
                      </div>
                    </div>
                    <div>
                      {isConnected ? (
                        <Badge className="bg-success-subtle text-success border-success-border">
                          <CheckCircle2 className="mr-1 h-3.5 w-3.5" />
                          {t('settings.connected')}
                        </Badge>
                      ) : (
                        <Badge className="bg-muted text-muted-foreground border-border">
                          {t('settings.notConnected')}
                        </Badge>
                      )}
                    </div>
                  </CardHeader>
                  <CardContent className="pb-4">
                    {isConnected ? (
                      <div className="space-y-2 text-sm text-muted-foreground bg-muted p-3 rounded-lg border border-border">
                        <div className="flex justify-between items-center py-0.5">
                          <span className="text-muted-foreground">{t('settings.account')}:</span>
                          <span className="font-medium text-foreground">{connection.email || t('settings.connectedAccount')}</span>
                        </div>
                        <div className="flex justify-between items-center py-0.5">
                          <span className="text-muted-foreground flex items-center gap-1">
                            <Calendar className="h-3.5 w-3.5" /> {t('settings.connectedOn')}:
                          </span>
                          <span>{new Date(connection.created_at).toLocaleDateString()}</span>
                        </div>
                        <div className="flex justify-between items-center py-0.5">
                          <span className="text-muted-foreground flex items-center gap-1">
                            <Clock className="h-3.5 w-3.5" /> {t('settings.lastAccessed')}:
                          </span>
                          <span>
                            {connection.updated_at
                              ? new Date(connection.updated_at).toLocaleString()
                              : t('settings.notAvailableShort')}
                          </span>
                        </div>
                      </div>
                    ) : (
                      <p className="text-sm text-muted-foreground">
                        {t('settings.linkAccountNotice', { provider: getProviderDisplayName(provider.name) })}
                      </p>
                    )}
                  </CardContent>
                  <CardFooter className="flex justify-end border-t border-border pt-4 bg-muted/50">
                    {isConnected ? (
                      <Button
                        variant="outline"
                        className="text-danger hover:text-danger hover:bg-danger-subtle border-danger-border"
                        onClick={() => setSelectedConnection(connection)}
                      >
                        <Trash2 className="mr-1.5 h-4 w-4" />
                        {t('settings.disconnect')}
                      </Button>
                    ) : (
                      <Button onClick={() => handleConnect(provider.name)}>
                        <RefreshCw className="mr-1.5 h-4 w-4" />
                        {t('settings.connectProvider')}
                      </Button>
                    )}
                  </CardFooter>
                </Card>
              );
            })}
          </div>
        </div>
      )}
    </div>

    {/* Disconnection Confirmation Dialog */}
      <Dialog open={!!selectedConnection} onOpenChange={(open) => !open && setSelectedConnection(null)}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-danger">
              <AlertTriangle className="h-5 w-5" />
              {t('settings.disconnectTitle')}
            </DialogTitle>
            <DialogDescription className="pt-2">
              {t('settings.disconnectDescription', { provider: selectedConnection ? getProviderDisplayName(selectedConnection.provider) : '' })}
            </DialogDescription>
          </DialogHeader>
          <div className="py-2 text-sm text-muted-foreground">
            {t('settings.disconnectNotice')}
          </div>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              variant="outline"
              onClick={() => setSelectedConnection(null)}
              disabled={isDisconnecting}
            >
              {t('common.cancel')}
            </Button>
            <Button
              className="bg-danger hover:bg-danger/90 text-danger-foreground"
              onClick={handleDisconnectConfirm}
              disabled={isDisconnecting}
            >
              {isDisconnecting ? (
                <>
                  <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
                  {t('settings.disconnecting')}
                </>
              ) : (
                t('settings.disconnect')
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default IntegrationsSettingsPage;
