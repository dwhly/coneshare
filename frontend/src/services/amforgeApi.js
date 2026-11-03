// AmForge Deal Suite API helpers (kept separate from services/api.js to ease upstream merges).
import api from './api';

export const getViewerOrganisations = () => api.get('/viewer-organisations/');
export const createViewerOrganisation = (data) => api.post('/viewer-organisations/', data);
export const updateViewerOrganisation = (id, data) => api.patch(`/viewer-organisations/${id}/`, data);
export const deleteViewerOrganisation = (id) => api.delete(`/viewer-organisations/${id}/`);

export const getShareLinkAccessGrants = (linkId) => api.get(`/share-links/${linkId}/access-grants/`);
export const addShareLinkAccessGrant = (linkId, data) => api.post(`/share-links/${linkId}/access-grants/`, data);
export const removeShareLinkAccessGrant = (linkId, grantId) =>
  api.delete(`/share-links/${linkId}/access-grants/${grantId}/`);
export const getShareLinkIssuedCopies = (linkId, params) =>
  api.get(`/share-links/${linkId}/issued-copies/`, { params });

export const duplicateDataroom = (id, data = {}) => api.post(`/datarooms/${id}/duplicate/`, data);
