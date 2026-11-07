import { useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Edit2,
  ImagePlus,
  Loader2,
  Trash2,
  X,
} from 'lucide-react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { ConfirmationDialog } from '../dialogs/ConfirmationDialog';
import {
  createDataroomBannerImage,
  deleteDataroomBannerImage,
  reorderDataroomBannerImages,
  updateDataroomBannerImage,
} from '../../services/api';

const MAX_BANNER_IMAGES = 10;
const MAX_BANNER_SIZE_BYTES = 5 * 1024 * 1024; // 5 MB
const ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp'];

export function DataroomBannerGalleryManager({
  dataroomId,
  images = [],
  onImagesChange,
  canManage = true,
}) {
  const { t } = useTranslation();
  const fileInputRef = useRef(null);

  const [isUploading, setIsUploading] = useState(false);
  const [editingImageId, setEditingImageId] = useState(null);
  const [editingCaption, setEditingCaption] = useState('');
  const [isSavingCaption, setIsSavingCaption] = useState(false);
  const [isReordering, setIsReordering] = useState(false);

  // Deletion modal state
  const [imageToDelete, setImageToDelete] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Drag and drop state
  const [draggedIndex, setDraggedIndex] = useState(null);

  const isAtMaxCapacity = images.length >= MAX_BANNER_IMAGES;

  const handleUploadFile = async (file) => {
    if (!file) return;

    if (!ALLOWED_IMAGE_TYPES.includes(file.type)) {
      toast.error(t('datarooms.unsupportedImageType', {
        defaultValue: 'Only JPG, PNG, and WebP images are allowed.',
      }));
      return;
    }

    if (file.size > MAX_BANNER_SIZE_BYTES) {
      toast.error(t('datarooms.imageSizeLimitExceeded', {
        defaultValue: 'Image size cannot exceed 5 MB.',
      }));
      return;
    }

    if (images.length >= MAX_BANNER_IMAGES) {
      toast.error(t('datarooms.galleryMaxReached', {
        defaultValue: 'Maximum of 10 banner images reached.',
      }));
      return;
    }

    setIsUploading(true);
    try {
      await createDataroomBannerImage(dataroomId, {
        image: file,
        caption: '',
      });
      toast.success(t('datarooms.imageUploadSuccess', {
        defaultValue: 'Banner image uploaded successfully.',
      }));
      if (onImagesChange) {
        await onImagesChange();
      }
    } catch {
      // Error handled by global axios interceptor
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleFileInputChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      handleUploadFile(file);
    }
  };

  const startEditCaption = (img) => {
    setEditingImageId(img.id);
    setEditingCaption(img.caption || '');
  };

  const cancelEditCaption = () => {
    setEditingImageId(null);
    setEditingCaption('');
  };

  const saveEditCaption = async (imageId) => {
    setIsSavingCaption(true);
    try {
      await updateDataroomBannerImage(dataroomId, imageId, {
        caption: editingCaption.trim(),
      });
      toast.success(t('datarooms.imageCaptionUpdated', {
        defaultValue: 'Caption updated.',
      }));
      setEditingImageId(null);
      if (onImagesChange) {
        await onImagesChange();
      }
    } catch {
      // Error handled by interceptor
    } finally {
      setIsSavingCaption(false);
    }
  };

  const handleMove = async (fromIndex, toIndex) => {
    if (toIndex < 0 || toIndex >= images.length || fromIndex === toIndex || isReordering) {
      return;
    }

    const reordered = [...images];
    const [moved] = reordered.splice(fromIndex, 1);
    reordered.splice(toIndex, 0, moved);

    setIsReordering(true);
    try {
      await reorderDataroomBannerImages(
        dataroomId,
        reordered.map((img, idx) => ({ id: img.id, position: idx }))
      );
      toast.success(t('datarooms.imagesReordered', {
        defaultValue: 'Banner images reordered.',
      }));
      if (onImagesChange) {
        await onImagesChange();
      }
    } catch {
      // Error handled by interceptor
    } finally {
      setIsReordering(false);
    }
  };

  const handleDragStart = (e, index) => {
    setDraggedIndex(index);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = async (e, targetIndex) => {
    e.preventDefault();
    if (draggedIndex === null || draggedIndex === targetIndex) {
      setDraggedIndex(null);
      return;
    }
    const from = draggedIndex;
    setDraggedIndex(null);
    await handleMove(from, targetIndex);
  };

  const handleDeleteConfirm = async () => {
    if (!imageToDelete) return;
    setIsDeleting(true);
    try {
      await deleteDataroomBannerImage(dataroomId, imageToDelete.id);
      toast.success(t('datarooms.imageDeleteSuccess', {
        defaultValue: 'Banner image deleted.',
      }));
      setImageToDelete(null);
      if (onImagesChange) {
        await onImagesChange();
      }
    } catch {
      // Error handled by interceptor
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Upload button & Capacity header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <p className="text-xs text-muted-foreground">
            {t('datarooms.bannerGalleryHelp', {
              defaultValue: 'Supports JPG, PNG, WebP up to 5 MB per image.',
            })}
          </p>
          <span className="text-xs font-semibold text-foreground">
            {images.length} / {MAX_BANNER_IMAGES} {t('common.images', { defaultValue: 'images' })}
          </span>
        </div>

        {canManage && (
          <div>
            <input
              ref={fileInputRef}
              type="file"
              accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"
              className="hidden"
              onChange={handleFileInputChange}
              disabled={isUploading || isAtMaxCapacity}
            />
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading || isAtMaxCapacity}
              className="gap-2 shrink-0"
              title={isAtMaxCapacity ? t('datarooms.galleryMaxReached') : undefined}
            >
              {isUploading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <ImagePlus className="h-4 w-4" />
              )}
              {isUploading
                ? t('datarooms.uploadingImage', { defaultValue: 'Uploading...' })
                : t('datarooms.addImage', { defaultValue: 'Add Image' })}
            </Button>
          </div>
        )}
      </div>

      {/* Grid of Banner Images */}
      {images.length === 0 ? (
        <div
          onClick={() => !isAtMaxCapacity && canManage && fileInputRef.current?.click()}
          className={`flex flex-col items-center justify-center p-8 border-2 border-dashed rounded-xl transition-colors ${
            canManage && !isAtMaxCapacity
              ? 'border-border/80 hover:border-primary/60 hover:bg-muted/40 cursor-pointer'
              : 'border-border/40 bg-muted/20'
          }`}
        >
          <ImagePlus className="h-10 w-10 text-muted-foreground mb-2" />
          <p className="text-sm font-medium text-foreground">
            {t('datarooms.noGalleryImages', {
              defaultValue: 'No banner images uploaded yet.',
            })}
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            {canManage
              ? t('datarooms.galleryManagerDescription', {
                  defaultValue: 'Upload up to 10 images to showcase in an interactive accordion banner on desktop and swipeable carousel on mobile.',
                })
              : ''}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {images.map((img, index) => {
            const isEditingThisCaption = editingImageId === img.id;
            return (
              <div
                key={img.id}
                draggable={canManage && !isEditingThisCaption && !isReordering}
                onDragStart={(e) => handleDragStart(e, index)}
                onDragOver={handleDragOver}
                onDrop={(e) => handleDrop(e, index)}
                className={`relative flex flex-col rounded-xl border border-border bg-card overflow-hidden shadow-xs transition-all ${
                  draggedIndex === index ? 'opacity-40 scale-95' : 'hover:shadow-md'
                }`}
              >
                {/* Image Preview Container */}
                <div className="relative aspect-[16/9] w-full bg-primary overflow-hidden">
                  <img
                    src={img.image_url || img.image}
                    alt={img.caption || `Banner ${index + 1}`}
                    className="h-full w-full object-cover"
                  />
                  {/* Order Badge */}
                  <span className="absolute top-2 left-2 bg-black/60 text-white text-[11px] font-semibold px-2 py-0.5 rounded-full backdrop-blur-xs">
                    #{index + 1}
                  </span>

                  {/* Actions overlay */}
                  {canManage && (
                    <div className="absolute top-2 right-2 flex items-center gap-1">
                      <Button
                        type="button"
                        size="icon"
                        variant="secondary"
                        className="h-7 w-7 rounded-full bg-white/90 text-danger hover:bg-danger-subtle hover:text-danger shadow-xs"
                        onClick={() => setImageToDelete(img)}
                        title={t('common.delete')}
                        aria-label={`Delete banner image ${index + 1}`}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  )}
                </div>

                {/* Card Footer: Caption & Reorder Controls */}
                <div className="p-3 flex flex-col gap-2 flex-1 justify-between bg-card">
                  {/* Caption Section */}
                  {isEditingThisCaption ? (
                    <div className="space-y-1.5">
                      <Input
                        value={editingCaption}
                        onChange={(e) => setEditingCaption(e.target.value)}
                        placeholder={t('datarooms.captionPlaceholder', {
                          defaultValue: 'Add a caption for this banner (optional)...',
                        })}
                        maxLength={255}
                        className="text-xs h-8"
                        autoFocus
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            e.preventDefault();
                            saveEditCaption(img.id);
                          } else if (e.key === 'Escape') {
                            cancelEditCaption();
                          }
                        }}
                      />
                      <div className="flex justify-end gap-1">
                        <Button
                          type="button"
                          size="sm"
                          variant="ghost"
                          className="h-6 px-2 text-xs"
                          onClick={cancelEditCaption}
                          disabled={isSavingCaption}
                        >
                          <X className="h-3 w-3 mr-1" />
                          {t('common.cancel')}
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          className="h-6 px-2 text-xs"
                          onClick={() => saveEditCaption(img.id)}
                          disabled={isSavingCaption}
                        >
                          {isSavingCaption ? (
                            <Loader2 className="h-3 w-3 animate-spin mr-1" />
                          ) : (
                            <Check className="h-3 w-3 mr-1" />
                          )}
                          {t('common.save')}
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-start justify-between gap-2 min-h-[32px]">
                      <p
                        className={`text-xs line-clamp-2 ${
                          img.caption ? 'text-foreground' : 'text-muted-foreground italic'
                        }`}
                        title={img.caption || ''}
                      >
                        {img.caption || t('datarooms.noCaption')}
                      </p>
                      {canManage && (
                        <button
                          type="button"
                          onClick={() => startEditCaption(img)}
                          className="shrink-0 text-muted-foreground hover:text-foreground transition-colors p-1"
                          title={t('datarooms.editCaption', { defaultValue: 'Edit caption' })}
                          aria-label={`Edit caption for banner image ${index + 1}`}
                        >
                          <Edit2 className="h-3 w-3" />
                        </button>
                      )}
                    </div>
                  )}

                  {/* Reorder Buttons */}
                  {canManage && (
                    <div className="flex items-center justify-end gap-1 border-t border-border/50 pt-2 mt-1">
                      <Button
                        type="button"
                        variant="outline"
                        size="icon"
                        className="h-6 w-6"
                        disabled={index === 0 || isReordering}
                        onClick={() => handleMove(index, index - 1)}
                        title={t('datarooms.moveLeft', { defaultValue: 'Move left' })}
                        aria-label={`Move banner image ${index + 1} left`}
                      >
                        <ArrowLeft className="h-3 w-3" />
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        size="icon"
                        className="h-6 w-6"
                        disabled={index === images.length - 1 || isReordering}
                        onClick={() => handleMove(index, index + 1)}
                        title={t('datarooms.moveRight', { defaultValue: 'Move right' })}
                        aria-label={`Move banner image ${index + 1} right`}
                      >
                        <ArrowRight className="h-3 w-3" />
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Confirmation Dialog for Image Deletion */}
      <ConfirmationDialog
        isOpen={Boolean(imageToDelete)}
        onOpenChange={(open) => !open && setImageToDelete(null)}
        title={t('datarooms.deleteImageConfirm', {
          defaultValue: 'Delete Banner Image?',
        })}
        description={t('datarooms.deleteImageConfirmDesc', {
          defaultValue: 'Are you sure you want to remove this image from the banner gallery?',
        })}
        confirmText={t('common.delete')}
        onConfirm={handleDeleteConfirm}
        isLoading={isDeleting}
      />
    </div>
  );
}
