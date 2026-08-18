package com.aicrm.common.util;

import java.io.File;

public class FileUtil {
    public static String getExtension(String fileName) {
        if (fileName == null) return "";
        int index = fileName.lastIndexOf('.');
        return index == -1 ? "" : fileName.substring(index + 1);
    }
}
