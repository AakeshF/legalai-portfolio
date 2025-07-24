import { lazy, ComponentType } from 'react';

// Utility to retry failed dynamic imports
export function lazyWithRetry<T extends ComponentType<any>>(
  componentImport: () => Promise<{ default: T }>
): React.LazyExoticComponent<T> {
  return lazy(async () => {
    const pageHasAlreadyBeenForceRefreshed = JSON.parse(
      window.sessionStorage.getItem('page-has-been-force-refreshed') || 'false'
    );

    try {
      const component = await componentImport();
      window.sessionStorage.setItem('page-has-been-force-refreshed', 'false');
      return component;
    } catch (error) {
      if (!pageHasAlreadyBeenForceRefreshed) {
        // Assuming that the user is not on the latest version of the application.
        // Let's refresh the page immediately.
        window.sessionStorage.setItem('page-has-been-force-refreshed', 'true');
        window.location.reload();
        
        // Return empty component while reloading
        return { default: (() => null) as T };
      }

      // The page has already been reloaded
      // Assuming that user is already using the latest version of the application.
      // Let's throw the error to the error boundary
      throw error;
    }
  });
}