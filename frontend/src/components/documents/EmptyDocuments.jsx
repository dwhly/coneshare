import { useTranslation } from "react-i18next";
import { UploadCloud as UploadIcon } from "lucide-react";

export function EmptyDocuments() {
  const { t } = useTranslation();

  return (
    <div className="py-24 text-center">
      <UploadIcon className="mx-auto h-16 w-16 text-muted-foreground" />
      <h3 className="mt-4 text-sm font-medium text-foreground">
        {t('documents.noDocuments')}
      </h3>
      <p className="mt-2 text-sm text-muted-foreground max-w-xs mx-auto">
        {t('documents.emptyStateNotice')}
      </p>
    </div>
  );
}
