/**
 * Login Page Tests including Logo Integration
 * 登录页面测试，包含logo集成功能
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Login from '../Login';

// Mock auth store
const mockIsAuthenticated = false;
const mockIsLoading = false;

jest.mock('../../stores/authStore', () => ({
  __esModule: true,
  default: () => ({
    isAuthenticated: mockIsAuthenticated,
    isLoading: mockIsLoading
  })
}));

// Mock OAuth retry handler
jest.mock('../../utils/oauthRetry', () => ({
  OAuthRetryHandler: {
    getOrCreateValidSession: jest.fn().mockResolvedValue({
      sessionId: 'test-session',
      authUrl: 'https://test-auth-url.com'
    })
  }
}));

// Helper to render with router
const renderWithRouter = (component: React.ReactElement) => {
  return render(
    <BrowserRouter>
      {component}
    </BrowserRouter>
  );
};

describe('Login Page Logo Integration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Mock window.location.href assignment
    delete (window as any).location;
    (window as any).location = { href: '' };
  });

  test('renders logo with correct attributes', () => {
    renderWithRouter(<Login />);
    const logo = screen.getByAltText('MailAssistant Logo');
    expect(logo).toHaveAttribute('src', '/logo.png');
    expect(logo).toHaveClass('mx-auto', 'h-16', 'w-16', 'sm:h-12', 'sm:w-12', 'mb-4', 'object-contain');
  });

  test('logo appears before welcome text', () => {
    renderWithRouter(<Login />);
    const logo = screen.getByAltText('MailAssistant Logo');
    const welcomeText = screen.getByText('Welcome to MailAssistant');
    
    // Logo should come before welcome text in DOM order
    expect(logo.compareDocumentPosition(welcomeText))
      .toBe(Node.DOCUMENT_POSITION_FOLLOWING);
  });

  test('renders login button and handles click', async () => {
    renderWithRouter(<Login />);
    const loginButton = screen.getByText('Sign in with Google');
    expect(loginButton).toBeInTheDocument();
    
    fireEvent.click(loginButton);
    // Button should show loading state
    expect(screen.getByRole('status', { hidden: true })).toBeInTheDocument();
  });

  test('displays feature list correctly', () => {
    renderWithRouter(<Login />);
    expect(screen.getByText('AI-powered email analysis and classification')).toBeInTheDocument();
    expect(screen.getByText('Daily intelligent email reports')).toBeInTheDocument();
    expect(screen.getByText('Conversational email management')).toBeInTheDocument();
    expect(screen.getByText('Bulk operations and smart filtering')).toBeInTheDocument();
  });

  test('displays security notice', () => {
    renderWithRouter(<Login />);
    expect(screen.getByText('Secure & Private')).toBeInTheDocument();
    expect(screen.getByText(/We use Google OAuth for secure authentication/)).toBeInTheDocument();
  });
});