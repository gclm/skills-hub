# Java TDD Example — Order Service with Spring Boot + Mockito

Scenario: Implement an `OrderService` that places orders with stock validation. If stock is insufficient, reject the order.

## Step 1: RED — Write failing tests first

```java
// src/test/java/com/example/order/OrderServiceTest.java
package com.example.order;

import org.junit.jupiter.api.*;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.*;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Optional;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class OrderServiceTest {

    @Mock
    private ProductRepository productRepo;

    @Mock
    private OrderRepository orderRepo;

    @InjectMocks
    private OrderService orderService;

    // --- Success case ---

    @Test
    @DisplayName("placeOrder: sufficient stock -> order created with CONFIRMED status")
    void placeOrder_sufficientStock_createsConfirmedOrder() {
        // Arrange
        Product product = new Product(1L, "Widget", 100, new Money("USD", 9.99));
        when(productRepo.findById(1L)).thenReturn(Optional.of(product));
        when(orderRepo.save(any())).thenAnswer(inv -> inv.getArgument(0));

        // Act
        Order result = orderService.placeOrder(1L, 5);

        // Assert
        assertThat(result.getStatus()).isEqualTo(OrderStatus.CONFIRMED);
        assertThat(result.getQuantity()).isEqualTo(5);
        assertThat(result.getTotal().amount()).isEqualTo(49.95);
        verify(productRepo).decreaseStock(1L, 5);
    }

    // --- Insufficient stock ---

    @Test
    @DisplayName("placeOrder: insufficient stock -> throws InsufficientStockException")
    void placeOrder_insufficientStock_throwsException() {
        Product product = new Product(1L, "Widget", 3, new Money("USD", 9.99));
        when(productRepo.findById(1L)).thenReturn(Optional.of(product));

        assertThatThrownBy(() -> orderService.placeOrder(1L, 5))
            .isInstanceOf(InsufficientStockException.class)
            .hasMessageContaining("Requested 5 but only 3 available");

        verify(productRepo, never()).decreaseStock(anyLong(), anyInt());
        verify(orderRepo, never()).save(any());
    }

    // --- Product not found ---

    @Test
    @DisplayName("placeOrder: product not found -> throws ProductNotFoundException")
    void placeOrder_productNotFound_throwsException() {
        when(productRepo.findById(999L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> orderService.placeOrder(999L, 1))
            .isInstanceOf(ProductNotFoundException.class);
    }
}
```

Run: `mvn test -Dtest=OrderServiceTest` or `./gradlew test --tests OrderServiceTest`

Expected: **FAIL** — classes don't exist yet.

## Step 2: GREEN — Minimal implementation

```java
// src/main/java/com/example/order/OrderService.java
package com.example.order;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional
public class OrderService {

    private final ProductRepository productRepo;
    private final OrderRepository orderRepo;

    public OrderService(ProductRepository productRepo, OrderRepository orderRepo) {
        this.productRepo = productRepo;
        this.orderRepo = orderRepo;
    }

    public Order placeOrder(Long productId, int quantity) {
        Product product = productRepo.findById(productId)
            .orElseThrow(ProductNotFoundException::new);

        if (product.getStock() < quantity) {
            throw new InsufficientStockException(
                "Requested %d but only %d available".formatted(quantity, product.getStock()));
        }

        productRepo.decreaseStock(productId, quantity);

        Order order = new Order(
            product,
            quantity,
            product.getPrice().multiply(quantity),
            OrderStatus.CONFIRMED
        );

        return orderRepo.save(order);
    }
}
```

```java
// Supporting classes (minimal, just enough to compile)

// Order.java
public record Order(Product product, int quantity, Money total, OrderStatus status) {}

// Money.java
public record Money(String currency, double amount) {
    public Money multiply(int qty) { return new Money(currency, amount * qty); }
}

// OrderStatus.java
public enum OrderStatus { CONFIRMED, CANCELLED }

// Product.java
public record Product(Long id, String name, int stock, Money price) {}

// ProductRepository.java
public interface ProductRepository {
    Optional<Product> findById(Long id);
    void decreaseStock(Long id, int quantity);
}

// OrderRepository.java
public interface OrderRepository {
    Order save(Order order);
}

// InsufficientStockException.java
public class InsufficientStockException extends RuntimeException {
    public InsufficientStockException(String msg) { super(msg); }
}

// ProductNotFoundException.java
public class ProductNotFoundException extends RuntimeException {}
```

Run: `mvn test -Dtest=OrderServiceTest`

Expected: **PASS**

## Step 3: REFACTOR

Possible refactorings:

1. Extract validation into `OrderValidator` if validation grows complex
2. `Money` should use `BigDecimal` instead of `double` for financial accuracy:

```java
// Money.java (refactored)
public record Money(String currency, BigDecimal amount) {
    public Money multiply(int qty) {
        return new Money(currency, amount.multiply(BigDecimal.valueOf(qty)));
    }
}
```

Run: `mvn test` — all tests still pass.

## Key Patterns Used

- **@DisplayName**: Human-readable test names in reports
- **AssertJ**: Fluent assertions (`assertThat`, `assertThatThrownBy`) — more readable than JUnit's `assertEquals`
- **Mockito @Mock/@InjectMocks**: Auto-mocks injected via constructor
- **verify(never())**: Assert side effects DON'T happen on error paths
- **Constructor injection**: No `@Autowired` on fields — Spring best practice
- **Record types**: Immutable value objects (Java 16+)
