import { Folder as FolderIcon } from "lucide-react";
import { Link } from "react-router-dom";
import { cn } from "../../lib/utils";
import { ActionsDropdown } from "./ActionsDropdown";

function FolderCard({ folder, onRename, onDelete, isSelected }) {
  return (
    <div
      className={cn(
        "relative flex w-full items-center space-x-3 rounded-lg border bg-card px-4 py-5 shadow-sm group-hover:border-input ",
        isSelected && "border-primary bg-primary/10 "
      )}
    >
      <div className="flex-shrink-0">
        <FolderIcon className="h-6 w-6 text-muted-foreground" />
      </div>
      <div className="min-w-0 flex-1">
        <Link to={`/documents/folders/${folder.id}`} className="focus:outline-none">
          <span className="absolute inset-0" aria-hidden="true" />
          <p className="text-sm font-medium text-foreground">
            {folder.name}
          </p>
          <p className="truncate text-sm text-muted-foreground">
            Folder
          </p>
        </Link>
      </div>
      <ActionsDropdown
        item={folder}
        type="folder"
        onRename={onRename}
        onDelete={onDelete}
      />
    </div>
  );
}

export default FolderCard;
