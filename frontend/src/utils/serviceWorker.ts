import { Workbox } from 'workbox-window';

let wb: Workbox | undefined;

export const registerServiceWorker = () => {
  if ('serviceWorker' in navigator && import.meta.env.PROD) {
    wb = new Workbox('/sw.js');

    // Add event listeners
    wb.addEventListener('installed', (event) => {
      if (!event.isUpdate) {
        console.log('Service worker installed for the first time');
      }
    });

    wb.addEventListener('waiting', () => {
      // Show update prompt to user
      const shouldUpdate = window.confirm(
        'A new version of Legal AI Assistant is available. Would you like to update now?'
      );
      
      if (shouldUpdate && wb) {
        wb.messageSkipWaiting();
        wb.addEventListener('controlling', () => {
          window.location.reload();
        });
      }
    });

    wb.addEventListener('activated', (event) => {
      if (event.isUpdate) {
        console.log('Service worker updated');
      }
    });

    // Register the service worker
    wb.register()
      .then((registration) => {
        console.log('Service worker registered:', registration);
      })
      .catch((error) => {
        console.error('Service worker registration failed:', error);
      });
  }
};

export const unregisterServiceWorker = async () => {
  if ('serviceWorker' in navigator) {
    const registrations = await navigator.serviceWorker.getRegistrations();
    for (const registration of registrations) {
      await registration.unregister();
    }
  }
};

// Check if update is available
export const checkForUpdates = () => {
  if (wb) {
    wb.update();
  }
};

// Get current service worker status
export const getServiceWorkerStatus = async (): Promise<'active' | 'waiting' | 'installing' | 'none'> => {
  if (!('serviceWorker' in navigator)) {
    return 'none';
  }

  const registration = await navigator.serviceWorker.getRegistration();
  if (!registration) {
    return 'none';
  }

  if (registration.active) {
    return 'active';
  } else if (registration.waiting) {
    return 'waiting';
  } else if (registration.installing) {
    return 'installing';
  }

  return 'none';
};