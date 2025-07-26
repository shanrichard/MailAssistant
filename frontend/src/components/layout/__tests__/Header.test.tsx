/**
 * Header Component Logo Integration Tests
 * 测试Header组件logo集成功能
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { Header } from '../Header';
import { ROUTES } from '../../../config';

// Mock auth store
const mockUser = { email: 'test@example.com' };
const mockLogout = jest.fn();

jest.mock('../../../stores/authStore', () => ({
  __esModule: true,
  default: () => ({
    user: mockUser,
    logout: mockLogout
  })
}));

// Mock useNavigate
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate
}));

// Helper to render with router
const renderWithRouter = (component: React.ReactElement) => {
  return render(
    <BrowserRouter>
      {component}
    </BrowserRouter>
  );
};

describe('Header Component Logo Integration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders logo image with correct attributes', () => {
    renderWithRouter(<Header />);
    const logo = screen.getByAltText('MailAssistant Logo');
    expect(logo.getAttribute('src')).toBe('/logo.png');
    expect(logo.className).toContain('h-8');
    expect(logo.className).toContain('w-8');
    expect(logo.className).toContain('object-contain');
  });

  test('logo button navigates to daily report', () => {
    renderWithRouter(<Header />);
    const logoButton = screen.getByLabelText('返回主页');
    fireEvent.click(logoButton);
    expect(mockNavigate).toHaveBeenCalledWith(ROUTES.DAILY_REPORT);
  });

  test('logo has proper accessibility attributes', () => {
    renderWithRouter(<Header />);
    const logoButton = screen.getByLabelText('返回主页');
    expect(logoButton).toBeTruthy();
    expect(logoButton.className).toContain('hover:opacity-80');
  });

  test('header maintains existing user menu functionality', () => {
    renderWithRouter(<Header />);
    // Verify user menu still exists
    expect(screen.getByText('test@example.com')).toBeInTheDocument();
    expect(screen.getByText('T')).toBeInTheDocument(); // First letter of email
  });
});