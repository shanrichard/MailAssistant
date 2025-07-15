/**
 * 404 Not Found Page
 * 404页面
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../config';

const NotFound: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <h1 className="text-9xl font-bold text-gray-200">404</h1>
          <h2 className="mt-4 text-2xl font-bold text-gray-900">Page Not Found</h2>
          <p className="mt-2 text-gray-600">
            The page you're looking for doesn't exist.
          </p>
          <div className="mt-6">
            <button
              onClick={() => navigate(ROUTES.DASHBOARD)}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
            >
              Go to Dashboard
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NotFound;