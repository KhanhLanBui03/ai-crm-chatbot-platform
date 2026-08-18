package com.aicrm.chatbot.entity;

import com.aicrm.common.enums.ChatbotStatus;
import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

@Entity
@Table(name = "chatbots")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Chatbot {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "business_id")
    private Long businessId;

    @Column(nullable = false)
    private String name;

    @Column(name = "system_prompt")
    private String systemPrompt;

    private Double temperature;

    @Column(name = "welcome_message")
    private String welcomeMessage;

    @Column(name = "primary_color")
    private String primaryColor;

    @Column(name = "avatar_url")
    private String avatarUrl;

    @Column(name = "embed_token", unique = true)
    private String embedToken;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private ChatbotStatus status;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;
}
