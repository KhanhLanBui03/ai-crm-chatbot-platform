package com.aicrm.document.service;

import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

@Service
public class FileStorageService {

    /**
     * Chức năng: Lưu trữ tệp tin vật lý lên hệ thống ổ đĩa máy chủ
     * - Trả về đường dẫn lưu tệp tin
     */
    public String storeFile(MultipartFile file) {
        // TODO: Dựng function lưu tệp tin vật lý
        return null;
    }

    /**
     * Chức năng: Xóa tệp tin vật lý khỏi máy chủ
     */
    public void deleteFile(String filePath) {
        // TODO: Dựng function xóa tệp vật lý
    }
}
