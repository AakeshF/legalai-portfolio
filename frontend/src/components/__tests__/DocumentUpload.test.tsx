import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import DocumentUpload from '../EnhancedDocumentUpload';
import { renderWithProviders } from '../../tests/utils';
import { documentService } from '../../services/document.service';
import { useToast } from '../Toast';

// Mock services
vi.mock('../../services/document.service');
vi.mock('../Toast');

describe('DocumentUpload', () => {
  const mockOnUploadComplete = vi.fn();
  const mockOnViewChange = vi.fn();
  const mockShowSuccess = vi.fn();
  const mockShowError = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (useToast as any).mockReturnValue({
      showSuccess: mockShowSuccess,
      showError: mockShowError,
      showInfo: vi.fn(),
    });
  });

  it('renders upload interface', () => {
    renderWithProviders(
      <DocumentUpload 
        onUploadComplete={mockOnUploadComplete}
        onViewChange={mockOnViewChange}
      />
    );

    expect(screen.getByText(/drag and drop files here/i)).toBeInTheDocument();
    expect(screen.getByText(/select files/i)).toBeInTheDocument();
    expect(screen.getByText(/supported formats/i)).toBeInTheDocument();
  });

  it('handles file selection via input', async () => {
    const user = userEvent.setup();
    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
    
    renderWithProviders(
      <DocumentUpload 
        onUploadComplete={mockOnUploadComplete}
        onViewChange={mockOnViewChange}
      />
    );

    const input = screen.getByLabelText(/select files/i) as HTMLInputElement;
    
    // Mock successful upload
    (documentService.uploadDocument as any).mockResolvedValueOnce({
      id: 1,
      filename: 'test.pdf',
      processing_status: 'processing',
    });

    await user.upload(input, file);

    await waitFor(() => {
      expect(documentService.uploadDocument).toHaveBeenCalledWith(file, 'general');
      expect(mockShowSuccess).toHaveBeenCalledWith('test.pdf uploaded successfully');
      expect(mockOnUploadComplete).toHaveBeenCalled();
    });
  });

  it('handles drag and drop', async () => {
    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
    
    renderWithProviders(
      <DocumentUpload 
        onUploadComplete={mockOnUploadComplete}
        onViewChange={mockOnViewChange}
      />
    );

    const dropzone = screen.getByText(/drag and drop files here/i).closest('div')!;
    
    // Mock successful upload
    (documentService.uploadDocument as any).mockResolvedValueOnce({
      id: 1,
      filename: 'test.pdf',
      processing_status: 'processing',
    });

    // Simulate drag over
    fireEvent.dragOver(dropzone);
    expect(dropzone.className).toContain('border-blue-500');

    // Simulate drop
    fireEvent.drop(dropzone, {
      dataTransfer: {
        files: [file],
      },
    });

    await waitFor(() => {
      expect(documentService.uploadDocument).toHaveBeenCalledWith(file, 'general');
    });
  });

  it('shows error for unsupported file types', async () => {
    const user = userEvent.setup();
    const file = new File(['test content'], 'test.exe', { type: 'application/exe' });
    
    renderWithProviders(
      <DocumentUpload 
        onUploadComplete={mockOnUploadComplete}
        onViewChange={mockOnViewChange}
      />
    );

    const input = screen.getByLabelText(/select files/i) as HTMLInputElement;
    
    await user.upload(input, file);

    // Should not call upload service for unsupported file
    expect(documentService.uploadDocument).not.toHaveBeenCalled();
  });

  it('handles upload errors', async () => {
    const user = userEvent.setup();
    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
    
    renderWithProviders(
      <DocumentUpload 
        onUploadComplete={mockOnUploadComplete}
        onViewChange={mockOnViewChange}
      />
    );

    const input = screen.getByLabelText(/select files/i) as HTMLInputElement;
    
    // Mock failed upload
    (documentService.uploadDocument as any).mockRejectedValueOnce(
      new Error('Upload failed')
    );

    await user.upload(input, file);

    await waitFor(() => {
      expect(mockShowError).toHaveBeenCalledWith('Upload failed', 'Upload failed');
    });
  });

  it('shows upload progress', async () => {
    const user = userEvent.setup();
    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
    
    renderWithProviders(
      <DocumentUpload 
        onUploadComplete={mockOnUploadComplete}
        onViewChange={mockOnViewChange}
      />
    );

    const input = screen.getByLabelText(/select files/i) as HTMLInputElement;
    
    // Mock delayed upload
    (documentService.uploadDocument as any).mockImplementation(
      () => new Promise(resolve => setTimeout(() => resolve({
        id: 1,
        filename: 'test.pdf',
        processing_status: 'processing',
      }), 100))
    );

    await user.upload(input, file);

    // Should show progress bar
    expect(screen.getByText('test.pdf')).toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toBeInTheDocument();

    await waitFor(() => {
      expect(mockShowSuccess).toHaveBeenCalled();
    });
  });

  it('handles multiple file uploads', async () => {
    const user = userEvent.setup();
    const files = [
      new File(['content1'], 'test1.pdf', { type: 'application/pdf' }),
      new File(['content2'], 'test2.pdf', { type: 'application/pdf' }),
    ];
    
    renderWithProviders(
      <DocumentUpload 
        onUploadComplete={mockOnUploadComplete}
        onViewChange={mockOnViewChange}
      />
    );

    const input = screen.getByLabelText(/select files/i) as HTMLInputElement;
    
    // Mock successful uploads
    (documentService.uploadDocument as any)
      .mockResolvedValueOnce({ id: 1, filename: 'test1.pdf', processing_status: 'processing' })
      .mockResolvedValueOnce({ id: 2, filename: 'test2.pdf', processing_status: 'processing' });

    await user.upload(input, files);

    await waitFor(() => {
      expect(documentService.uploadDocument).toHaveBeenCalledTimes(2);
      expect(mockOnUploadComplete).toHaveBeenCalledTimes(2);
    });
  });
});