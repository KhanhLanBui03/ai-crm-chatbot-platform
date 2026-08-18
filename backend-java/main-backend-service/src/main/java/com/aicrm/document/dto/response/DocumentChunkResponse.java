package com.aicrm.document.dto.response;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class DocumentChunkResponse {
    private Long id;
    private String content;
    private Integer chunkIndex;
    private String vectorId;
}
