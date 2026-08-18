package com.aicrm.integration.ai;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class AiDocumentProcessResponse {
    private boolean success;
    private int chunksCount;
    private List<String> extractedChunks;
}
