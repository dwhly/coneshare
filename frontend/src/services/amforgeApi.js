// AmForge Deal Suite API helpers (kept separate from services/api.js to ease upstream merges).
import api from './api';

// Defer every call into a promise so callers can always .then/.catch, even when `api`
// is mocked or unavailable (e.g. upstream unit tests that mock services/api wholesale).
const call = (fn) =>
  new Promise((resolve, reject) => {
    try {
      resolve(fn());
    } catch (e) {
      reject(e);
    }
  });

export const getViewerOrganisations = () => call(() => api.get('/viewer-organisations/'));
export const createViewerOrganisation = (data) => call(() => api.post('/viewer-organisations/', data));
export const updateViewerOrganisation = (id, data) => call(() => api.patch(`/viewer-organisations/${id}/`, data));
export const deleteViewerOrganisation = (id) => call(() => api.delete(`/viewer-organisations/${id}/`));

export const getShareLinkAccessGrants = (linkId) => call(() => api.get(`/share-links/${linkId}/access-grants/`));
export const addShareLinkAccessGrant = (linkId, data) => call(() => api.post(`/share-links/${linkId}/access-grants/`, data));
export const removeShareLinkAccessGrant = (linkId, grantId) =>
  call(() => api.delete(`/share-links/${linkId}/access-grants/${grantId}/`));
export const getShareLinkIssuedCopies = (linkId, params) =>
  call(() => api.get(`/share-links/${linkId}/issued-copies/`, { params }));

export const duplicateDataroom = (id, data = {}) => call(() => api.post(`/datarooms/${id}/duplicate/`, data));
